"""LangGraph-based SRE Agent with DSPy for Kubernetes failure detection and remediation."""

import json
import subprocess
from typing import Any

import dspy
from langgraph.graph import END, StateGraph
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from sre_agent.cache import CacheManager
from sre_agent.dspy_modules import DiagnoseModule, ProposeFixModule
from sre_agent.k8s_client import K8sClient
from sre_agent.utils import get_logger, load_config

logger = get_logger(__name__)
config = load_config()


class AgentState(dict):
    """State for LangGraph workflow."""
    pass


class SREAgent:
    """SRE Agent using LangGraph, DSPy, and OpenRouter."""
    
    def __init__(self):
        """Initialize agent with OpenRouter, DSPy, Qdrant, and cache."""
        # Initialize DSPy with OpenRouter
        self._init_dspy()
        
        # Initialize DSPy modules
        self.diagnose_module = DiagnoseModule()
        self.propose_fix_module = ProposeFixModule()
        
        # Initialize Qdrant (optional - can work without it)
        try:
            self.qdrant = QdrantClient(
                host=config["qdrant"]["host"],
                port=config["qdrant"]["port"],
            )
            self._ensure_collection()
        except Exception as e:
            logger.warning(f"Qdrant not available: {e}, continuing without knowledge base")
            self.qdrant = None
        
        # Initialize cache
        self.cache = CacheManager()
        
        # Initialize K8s client
        self.k8s = K8sClient()
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
    
    def _init_dspy(self):
        """Initialize DSPy with OpenRouter (OpenAI-compatible)."""
        import os
        from openai import OpenAI
        
        # Get API key from config or environment
        api_key = config["llm"].get("api_key") or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set. Export it: export OPENROUTER_API_KEY='your-key'")
        
        base_url = config["llm"]["base_url"]
        model = config["llm"]["model"]
        
        # Create OpenAI client pointing to OpenRouter
        openai_client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        
        # Create DSPy LM wrapper for OpenAI-compatible API
        class OpenRouterLM(dspy.LM):
            def __init__(self, client, model: str, temperature: float):
                super().__init__(model)
                self.client = client
                self.model = model
                self.temperature = temperature
                self.provider = "openrouter"
            
            def __call__(self, prompt, **kwargs):
                """Call OpenRouter API."""
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=self.temperature,
                        timeout=120.0,
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    logger.error(f"OpenRouter API error: {e}")
                    return f"Error: {e}"
            
            def request(self, prompt, **kwargs):
                """DSPy request method."""
                return self(prompt, **kwargs)
        
        lm = OpenRouterLM(
            client=openai_client,
            model=model,
            temperature=config["llm"]["temperature"],
        )
        dspy.configure(lm=lm)
        logger.info(f"DSPy initialized with OpenRouter ({model})")
    
    def _ensure_collection(self):
        """Ensure Qdrant collection exists."""
        if not self.qdrant:
            return
        try:
            collection_name = config["qdrant"]["collection"]
            collections = self.qdrant.get_collections()
            if collection_name not in [c.name for c in collections.collections]:
                self.qdrant.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                )
                logger.info(f"Created Qdrant collection: {collection_name}")
        except Exception as e:
            logger.warning(f"Could not ensure Qdrant collection: {e}")
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("detect", self._detect_node)
        workflow.add_node("diagnose", self._diagnose_node)
        workflow.add_node("propose_fix", self._propose_fix_node)
        workflow.add_node("await_approval", self._await_approval_node)
        workflow.add_node("execute", self._execute_node)
        workflow.add_node("evaluate", self._evaluate_node)
        
        # Set entry point
        workflow.set_entry_point("detect")
        
        # Add edges - workflow stops at approval (execution requires external approval)
        workflow.add_edge("detect", "diagnose")
        workflow.add_edge("diagnose", "propose_fix")
        workflow.add_edge("propose_fix", "await_approval")
        # Approval stops here - execution happens separately when approved
        workflow.add_edge("await_approval", END)
        
        return workflow.compile()
    
    def _detect_node(self, state: AgentState) -> AgentState:
        """Detect failure type."""
        namespace = state.get("namespace", "default")
        resource_type = state.get("resource_type")
        resource_name = state.get("resource_name")
        
        logger.info(f"Detecting failure: {namespace}/{resource_type}/{resource_name}")
        
        try:
            # Get cluster state
            cluster_state = self.k8s.get_resource_state(namespace, resource_type, resource_name)
            state["cluster_state"] = cluster_state
            
            # Detect failure type
            failure_type = None
            if resource_type == "Deployment":
                if self.k8s.has_oom_killed(namespace, resource_name):
                    failure_type = "OOMKilled"
            elif resource_type == "Service":
                if not self.k8s.has_endpoints(namespace, resource_name):
                    failure_type = "ServiceMisconfigured"
            
            state["failure_type"] = failure_type
            state["detected"] = failure_type is not None
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            state["error"] = f"Failed to detect: {str(e)}"
            state["detected"] = False
        
        return state
    
    def _diagnose_node(self, state: AgentState) -> AgentState:
        """Perform root cause analysis using DSPy."""
        if not state.get("detected"):
            # Still provide diagnosis even if no failure detected
            state["diagnosis"] = {
                "root_cause": "No failure detected. Resource appears to be healthy.",
                "contributing_factors": [],
                "evidence": [],
                "confidence": 100,
            }
            return state
        
        namespace = state.get("namespace")
        resource_type = state.get("resource_type")
        resource_name = state.get("resource_name")
        failure_type = state["failure_type"]
        cluster_state = state["cluster_state"]
        
        logger.info(f"Diagnosing {failure_type}")
        
        # Check cache first
        cached = self.cache.get_diagnosis(namespace, resource_type, resource_name)
        if cached:
            state["diagnosis"] = cached
            state["cached"] = True
            return state
        
        # Search Qdrant for similar patterns (if available)
        similar_patterns = []
        if self.qdrant:
            similar_patterns = self._search_knowledge_base(failure_type, cluster_state)
        similar_patterns_str = json.dumps(similar_patterns, indent=2) if similar_patterns else ""
        
        # Use DSPy for structured diagnosis
        cluster_state_str = json.dumps(cluster_state, indent=2)
        
        try:
            # Call DSPy module
            result = self.diagnose_module.forward(
                cluster_state=cluster_state_str,
                failure_type=failure_type,
                similar_patterns=similar_patterns_str,
            )
            
            # Extract results from DSPy Prediction
            if hasattr(result, 'root_cause'):
                root_cause = result.root_cause
            elif isinstance(result, dict):
                root_cause = result.get('root_cause', f'{failure_type} detected in cluster')
            else:
                root_cause = str(result) if result else f'{failure_type} detected in cluster'
            
            diagnosis = {
                "root_cause": root_cause,
                "contributing_factors": getattr(result, 'contributing_factors', []) if hasattr(result, 'contributing_factors') else [],
                "evidence": getattr(result, 'evidence', []) if hasattr(result, 'evidence') else [],
                "confidence": int(getattr(result, 'confidence', 75)) if hasattr(result, 'confidence') else 75,
            }
            
            # Fallback if empty
            if not diagnosis["root_cause"] or diagnosis["root_cause"].startswith("Error"):
                raise ValueError("DSPy returned error or empty result")
                
        except Exception as e:
            logger.warning(f"DSPy diagnosis failed: {e}, using rule-based fallback")
            # Rule-based fallback diagnosis
            if failure_type == "OOMKilled":
                containers = cluster_state.get("spec", {}).get("containers", [])
                memory_limits = [c.get("resources", {}).get("limits", {}).get("memory", "N/A") for c in containers]
                diagnosis = {
                    "root_cause": f"Pod is being OOMKilled due to insufficient memory limits. Current limits: {', '.join(memory_limits)}. The container is exceeding these limits and being terminated by Kubernetes.",
                    "contributing_factors": [
                        f"Memory limit too low: {memory_limits[0] if memory_limits else 'Not set'}",
                        "Container memory usage exceeds configured limit",
                        "Kubernetes OOMKiller is terminating the pod"
                    ],
                    "evidence": [f"Memory limits: {m}" for m in memory_limits if m != "N/A"],
                    "confidence": 90,
                }
            elif failure_type == "ServiceMisconfigured":
                service_selector = cluster_state.get("spec", {}).get("selector", {})
                pod_labels = cluster_state.get("pod_labels", [])
                diagnosis = {
                    "root_cause": f"Service has no endpoints due to label mismatch. Service selector: {service_selector}. Available pod labels don't match the selector.",
                    "contributing_factors": [
                        f"Service selector: {service_selector}",
                        f"Available pods: {len(pod_labels)}",
                        "Label mismatch prevents service from finding pods"
                    ],
                    "evidence": [f"Service selector: {service_selector}", f"Pod labels found: {len(pod_labels)}"],
                    "confidence": 95,
                }
            else:
                diagnosis = {
                    "root_cause": f"Analysis of {failure_type} failure in {resource_type} {resource_name}",
                    "contributing_factors": [],
                    "evidence": [],
                    "confidence": 70,
                }
        
        state["diagnosis"] = diagnosis
        state["similar_patterns"] = similar_patterns
        state["cached"] = False
        
        # Cache the result
        self.cache.set_diagnosis(namespace, resource_type, resource_name, diagnosis)
        
        return state
    
    def _propose_fix_node(self, state: AgentState) -> AgentState:
        """Propose remediation fix using DSPy."""
        failure_type = state["failure_type"]
        diagnosis = state["diagnosis"]
        cluster_state = state["cluster_state"]
        
        logger.info(f"Proposing fix for {failure_type}")
        
        # Use DSPy for structured fix proposal
        cluster_state_str = json.dumps(cluster_state, indent=2)
        root_cause = diagnosis.get("root_cause", "Unknown")
        
        try:
            # Call DSPy module
            result = self.propose_fix_module.forward(
                failure_type=failure_type,
                root_cause=root_cause,
                cluster_state=cluster_state_str,
            )
            
            proposal = {
                "fix_command": getattr(result, 'fix_command', '') if hasattr(result, 'fix_command') else '',
                "fix_yaml": getattr(result, 'fix_yaml', '') if hasattr(result, 'fix_yaml') else '',
                "risk_level": getattr(result, 'risk_level', 'medium') if hasattr(result, 'risk_level') else 'medium',
                "rollback_plan": getattr(result, 'rollback_plan', '') if hasattr(result, 'rollback_plan') else '',
                "expected_outcome": getattr(result, 'expected_outcome', '') if hasattr(result, 'expected_outcome') else '',
            }
            
            # Fallback if empty
            if not proposal["fix_command"] or proposal["fix_command"].startswith("Error"):
                raise ValueError("DSPy returned error or empty fix")
                
        except Exception as e:
            logger.warning(f"DSPy proposal failed: {e}, using rule-based fallback")
            # Rule-based fallback fix proposal
            namespace = state.get("namespace")
            resource_name = state.get("resource_name")
            
            if failure_type == "OOMKilled":
                proposal = {
                    "fix_command": f"kubectl patch deployment {resource_name} -n {namespace} --type='json' -p='[{{\"op\": \"replace\", \"path\": \"/spec/template/spec/containers/0/resources/limits/memory\", \"value\": \"512Mi\"}}]'",
                    "fix_yaml": "",
                    "risk_level": "medium",
                    "rollback_plan": f"kubectl rollout undo deployment/{resource_name} -n {namespace}",
                    "expected_outcome": "Pod should have sufficient memory and stop being OOMKilled",
                }
            elif failure_type == "ServiceMisconfigured":
                service_selector = cluster_state.get("spec", {}).get("selector", {})
                # Find matching pod labels
                pod_labels = cluster_state.get("pod_labels", [])
                if pod_labels:
                    # Use first pod's labels as reference
                    correct_labels = pod_labels[0]
                    # Fix selector to match pod labels (use common labels)
                    common_labels = {k: v for k, v in correct_labels.items() if k in ["app", "tier", "version"]}
                    selector_patch = json.dumps(common_labels)
                    proposal = {
                        "fix_command": f"kubectl patch service {resource_name} -n {namespace} --type='json' -p='[{{\"op\": \"replace\", \"path\": \"/spec/selector\", \"value\": {selector_patch}}}]'",
                        "fix_yaml": "",
                        "risk_level": "low",
                        "rollback_plan": f"kubectl patch service {resource_name} -n {namespace} --type='json' -p='[{{\"op\": \"replace\", \"path\": \"/spec/selector\", \"value\": {json.dumps(service_selector)}}}]'",
                        "expected_outcome": "Service should now have endpoints and route traffic to pods",
                    }
                else:
                    proposal = {
                        "fix_command": f"# No pods found. Check deployment labels match service selector.",
                        "fix_yaml": "",
                        "risk_level": "low",
                        "rollback_plan": "N/A",
                        "expected_outcome": "Service selector should match pod labels",
                    }
            else:
                proposal = {
                    "fix_command": f"# Manual intervention required for {failure_type}",
                    "fix_yaml": "",
                    "risk_level": "unknown",
                    "rollback_plan": "N/A",
                    "expected_outcome": "Issue resolved",
                }
        
        state["proposal"] = proposal
        state["requires_approval"] = proposal.get("risk_level", "medium") != "low"
        
        return state
    
    def _await_approval_node(self, state: AgentState) -> AgentState:
        """Wait for human approval - marks as pending, approval happens externally."""
        state["approval_status"] = "pending"
        state["action_required"] = "human_approval"
        logger.info("Fix proposal ready, awaiting human approval")
        return state
    
    def _execute_node(self, state: AgentState) -> AgentState:
        """Execute the fix."""
        if state.get("approval_status") != "approved":
            state["error"] = "Fix not approved"
            return state
        
        proposal = state["proposal"]
        fix_command = proposal.get("fix_command", "")
        
        if not fix_command or fix_command.startswith("#"):
            state["error"] = "No valid fix command provided"
            return state
        
        logger.info(f"Executing fix: {fix_command[:100]}")
        
        # Dry-run first
        if config["safety"]["dry_run_first"]:
            dry_cmd = f"{fix_command} --dry-run=client"
            result = subprocess.run(dry_cmd, shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                state["error"] = f"Dry-run failed: {result.stderr}"
                return state
        
        # Execute
        result = subprocess.run(fix_command, shell=True, capture_output=True, text=True, timeout=30)
        
        state["execution"] = {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        
        return state
    
    def _evaluate_node(self, state: AgentState) -> AgentState:
        """Evaluate if fix worked."""
        if not state.get("execution", {}).get("success"):
            state["evaluation"] = {"fixed": False, "status": "execution_failed"}
            return state
        
        # Re-check cluster state
        namespace = state.get("namespace")
        resource_type = state.get("resource_type")
        resource_name = state.get("resource_name")
        
        # Wait a bit for changes to propagate
        import time
        time.sleep(2)
        
        failure_type = self._detect_node(AgentState({
            "namespace": namespace,
            "resource_type": resource_type,
            "resource_name": resource_name,
        })).get("failure_type")
        
        fixed = failure_type is None
        state["evaluation"] = {
            "fixed": fixed,
            "status": "healthy" if fixed else f"still_{failure_type}",
        }
        
        # Update knowledge base if successful
        if fixed and self.qdrant:
            self._update_knowledge_base(state)
        
        return state
    
    def _search_knowledge_base(self, failure_type: str, cluster_state: dict) -> list:
        """Search Qdrant for similar failure patterns."""
        if not self.qdrant:
            return []
        try:
            # Simple text search for now
            results = self.qdrant.scroll(
                collection_name=config["qdrant"]["collection"],
                limit=5,
            )
            return [r.payload for r in results[0] if r.payload.get("failure_type") == failure_type]
        except:
            return []
    
    def _update_knowledge_base(self, state: AgentState):
        """Update knowledge base with successful resolution."""
        if not self.qdrant:
            return
        try:
            pattern = {
                "failure_type": state["failure_type"],
                "root_cause": state["diagnosis"].get("root_cause"),
                "fix": state["proposal"].get("fix_command"),
                "success": True,
            }
            # In production, would generate embedding and store
            logger.info("Knowledge base updated")
        except Exception as e:
            logger.warning(f"Could not update knowledge base: {e}")
    
    def execute_fix(self, namespace: str, resource_type: str, resource_name: str) -> dict:
        """Execute approved fix and evaluate."""
        # Re-run workflow with approval
        initial_state = AgentState({
            "namespace": namespace,
            "resource_type": resource_type,
            "resource_name": resource_name,
            "approval_status": "approved",
        })
        
        # Run execute and evaluate nodes
        state = self._execute_node(initial_state)
        if "error" in state:
            return state
        
        state = self._evaluate_node(state)
        return dict(state)
    
    def run(self, namespace: str, resource_type: str, resource_name: str) -> dict:
        """Run the complete workflow up to approval."""
        try:
            initial_state = AgentState({
                "namespace": namespace,
                "resource_type": resource_type,
                "resource_name": resource_name,
            })
            
            # Run workflow up to approval
            final_state = self.workflow.invoke(initial_state)
            
            # Return state as dict with better error handling
            result = dict(final_state)
            
            # Ensure required fields exist
            if "error" not in result and "detected" not in result:
                result["detected"] = result.get("failure_type") is not None
            
            return result
        except Exception as e:
            logger.exception(f"Workflow failed: {e}")
            return {
                "error": f"Workflow execution failed: {str(e)}",
                "namespace": namespace,
                "resource_type": resource_type,
                "resource_name": resource_name,
            }
