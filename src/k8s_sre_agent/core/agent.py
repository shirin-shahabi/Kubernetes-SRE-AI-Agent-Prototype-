"""LangGraph SRE Agent for Kubernetes failure detection and remediation.

Based on: https://arxiv.org/pdf/2509.02449 (KubeIntellect)
"""

import json
import os
from typing import Any

import dspy
from langgraph.graph import END, StateGraph
from openai import OpenAI

from k8s_sre_agent.core.state import AgentState, create_initial_state
from k8s_sre_agent.k8s.client import K8sClient
from k8s_sre_agent.knowledge.vector_store import VectorStore
from k8s_sre_agent.utils.cache import CacheManager
from k8s_sre_agent.utils.config import get_config
from k8s_sre_agent.utils.logging import get_logger

logger = get_logger(__name__)


class DiagnoseSignature(dspy.Signature):
    """Diagnose Kubernetes failure."""
    cluster_state: str = dspy.InputField(desc="K8s resource state JSON")
    failure_type: str = dspy.InputField(desc="OOMKilled or ServiceMisconfigured")
    root_cause: str = dspy.OutputField(desc="Root cause analysis")
    confidence: int = dspy.OutputField(desc="Confidence 0-100")


class ProposeFixSignature(dspy.Signature):
    """Propose fix for K8s failure."""
    failure_type: str = dspy.InputField()
    root_cause: str = dspy.InputField()
    cluster_state: str = dspy.InputField()
    fix_command: str = dspy.OutputField(desc="kubectl command to fix")
    risk_level: str = dspy.OutputField(desc="safe, moderate, or dangerous")
    rollback: str = dspy.OutputField(desc="Rollback command")


class SREAgent:
    """Kubernetes SRE Agent using LangGraph and DSPy."""
    
    def __init__(self) -> None:
        self.config = get_config()
        self.k8s = K8sClient()
        self.vector_store = VectorStore()
        self.cache = CacheManager()
        
        self._init_dspy()
        self.diagnose = dspy.ChainOfThought(DiagnoseSignature)
        self.propose = dspy.ChainOfThought(ProposeFixSignature)
        self.workflow = self._build_workflow()
        
        logger.info("sre_agent_initialized")
    
    def _init_dspy(self) -> None:
        """Initialize DSPy with OpenRouter."""
        llm_cfg = self.config.get("llm", {})
        api_key = llm_cfg.get("api_key") or os.getenv("OPENROUTER_API_KEY")
        
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        
        client = OpenAI(api_key=api_key, base_url=llm_cfg.get("base_url", "https://openrouter.ai/api/v1"))
        model = llm_cfg.get("model", "openai/gpt-4o-mini")
        
        class OpenRouterLM(dspy.LM):
            def __init__(self, c, m, t):
                super().__init__(m)
                self.client, self.model, self.temp = c, m, t
            
            def __call__(self, prompt, **kw):
                try:
                    r = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=self.temp,
                        timeout=120.0,
                    )
                    return r.choices[0].message.content
                except Exception as e:
                    return f"Error: {e}"
        
        dspy.configure(lm=OpenRouterLM(client, model, llm_cfg.get("temperature", 0.1)))
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow."""
        wf = StateGraph(AgentState)
        
        wf.add_node("detect", self._detect)
        wf.add_node("diagnose", self._diagnose)
        wf.add_node("plan", self._plan)
        wf.add_node("await_approval", self._await_approval)
        wf.add_node("execute", self._execute)
        wf.add_node("evaluate", self._evaluate)
        
        wf.set_entry_point("detect")
        wf.add_conditional_edges("detect", lambda s: "diagnose" if s.get("detected") else "end", {"diagnose": "diagnose", "end": END})
        wf.add_edge("diagnose", "plan")
        wf.add_edge("plan", "await_approval")
        wf.add_conditional_edges("await_approval", lambda s: "execute" if s.get("approval_status") == "approved" else "end", {"execute": "execute", "end": END})
        wf.add_edge("execute", "evaluate")
        wf.add_edge("evaluate", END)
        
        return wf.compile()
    
    def _detect(self, state: AgentState) -> AgentState:
        """Detect failure type."""
        ns, rt, rn = state["namespace"], state["resource_type"], state["resource_name"]
        logger.info("detect", resource=f"{ns}/{rt}/{rn}")
        
        state["cluster_state"] = self.k8s.get_resource_state(ns, rt, rn)
        
        failure = None
        if rt == "Deployment" and self.k8s.has_oom_killed(ns, rn):
            failure = "OOMKilled"
        elif rt == "Service" and not self.k8s.has_endpoints(ns, rn):
            failure = "ServiceMisconfigured"
        
        state["failure_type"] = failure
        state["detected"] = failure is not None
        return state
    
    def _diagnose(self, state: AgentState) -> AgentState:
        """Diagnose root cause using DSPy."""
        ns, rt, rn = state["namespace"], state["resource_type"], state["resource_name"]
        
        cached = self.cache.get_diagnosis(ns, rt, rn)
        if cached:
            state["diagnosis"] = cached
            return state
        
        try:
            result = self.diagnose(
                cluster_state=json.dumps(state["cluster_state"]),
                failure_type=state["failure_type"],
            )
            diagnosis = {"root_cause": result.root_cause, "confidence": int(result.confidence)}
        except Exception as e:
            diagnosis = {"root_cause": f"Analysis failed: {e}", "confidence": 50}
        
        state["diagnosis"] = diagnosis
        self.cache.set_diagnosis(ns, rt, rn, diagnosis)
        return state
    
    def _plan(self, state: AgentState) -> AgentState:
        """Generate action plan."""
        ns, rn = state["namespace"], state["resource_name"]
        ft = state["failure_type"]
        
        steps = []
        if ft == "OOMKilled":
            steps.append({
                "description": "Increase memory limit",
                "command": f"kubectl patch deployment {rn} -n {ns} --type=json -p='[{{\"op\": \"replace\", \"path\": \"/spec/template/spec/containers/0/resources/limits/memory\", \"value\": \"512Mi\"}}]'",
                "probability": 0.85,
                "risk_level": "safe",
                "rollback": f"kubectl rollout undo deployment/{rn} -n {ns}",
            })
        elif ft == "ServiceMisconfigured":
            selector = state["cluster_state"].get("spec", {}).get("selector", {})
            steps.append({
                "description": "Fix service selector",
                "command": f"kubectl patch svc {rn} -n {ns} -p '{{\"spec\":{{\"selector\":{{\"app\":\"{rn}\"}}}}}}'",
                "probability": 0.80,
                "risk_level": "safe",
                "rollback": f"kubectl patch svc {rn} -n {ns} -p '{{\"spec\":{{\"selector\":{json.dumps(selector)}}}}}'",
            })
        
        state["action_steps"] = steps
        return state
    
    def _await_approval(self, state: AgentState) -> AgentState:
        """Wait for human approval."""
        state["approval_status"] = "pending"
        return state
    
    def _execute(self, state: AgentState) -> AgentState:
        """Execute approved fix."""
        if not state.get("action_steps"):
            state["error"] = "No action steps"
            return state
        
        step = state["action_steps"][0]
        dry_run_first = self.config.get("safety", {}).get("dry_run_first", True)
        
        if dry_run_first:
            dry = self.k8s.execute(step["command"], dry_run=True)
            if not dry.get("success"):
                state["execution_result"] = {"success": False, "error": dry.get("stderr", "Dry run failed")}
                return state
        
        result = self.k8s.execute(step["command"])
        state["execution_result"] = result
        return state
    
    def _evaluate(self, state: AgentState) -> AgentState:
        """Evaluate if fix worked."""
        if not state.get("execution_result", {}).get("success"):
            state["evaluation"] = {"fixed": False, "status": "execution_failed"}
            return state
        
        ns, rt, rn = state["namespace"], state["resource_type"], state["resource_name"]
        ft = state["failure_type"]
        
        still_failing = False
        if rt == "Deployment" and ft == "OOMKilled":
            still_failing = self.k8s.has_oom_killed(ns, rn)
        elif rt == "Service" and ft == "ServiceMisconfigured":
            still_failing = not self.k8s.has_endpoints(ns, rn)
        
        state["evaluation"] = {"fixed": not still_failing, "status": "healthy" if not still_failing else f"still_{ft}"}
        
        if not still_failing:
            self.vector_store.add_pattern({
                "failure_type": ft,
                "root_cause": state["diagnosis"]["root_cause"],
                "fix": state["action_steps"][0]["command"],
            })
            self.cache.invalidate(ns, rt, rn)
        
        return state
    
    # Public API
    def run(self, namespace: str, resource_type: str, resource_name: str) -> dict[str, Any]:
        """Run complete workflow."""
        return dict(self.workflow.invoke(create_initial_state(namespace, resource_type, resource_name)))
    
    def run_until_approval(self, namespace: str, resource_type: str, resource_name: str) -> dict[str, Any]:
        """Run until approval gate."""
        state = create_initial_state(namespace, resource_type, resource_name)
        state = self._detect(state)
        if state.get("detected"):
            state = self._diagnose(state)
            state = self._plan(state)
            state = self._await_approval(state)
        return dict(state)
    
    def resume_with_approval(self, state: dict[str, Any], approved: bool) -> dict[str, Any]:
        """Resume after approval."""
        state["approval_status"] = "approved" if approved else "rejected"
        if approved:
            state = self._execute(state)
            state = self._evaluate(state)
        return dict(state)
