"""Gradio web interface with visual scenario viewer."""

import json

import gradio as gr

from sre_agent.agent import SREAgent
from sre_agent.utils import get_logger

logger = get_logger(__name__)
pending_actions = {}


def diagnose_ui(namespace: str, resource_type: str, resource_name: str):
    """Diagnose a resource."""
    try:
        if not namespace or not resource_name:
            return "⚠️ Please fill in Namespace and Resource Name", "", "", "Error: Missing fields", ""
        
        logger.info(f"Diagnosing {resource_type} {resource_name} in {namespace}")
        agent = SREAgent()
        result = agent.run(namespace, resource_type, resource_name)
        
        if "error" in result:
            error_msg = f"❌ **Error**: {result['error']}"
            return error_msg, "", "", "Error occurred", ""
        
        action_id = f"{namespace}-{resource_type}-{resource_name}"
        pending_actions[action_id] = result
        
        # Format diagnosis with color coding
        failure_type = result.get("failure_type", "None")
        color = "🔴" if failure_type else "🟢"
        
        diagnosis_data = result.get('diagnosis', {})
        root_cause = diagnosis_data.get('root_cause', 'N/A')
        confidence = diagnosis_data.get('confidence', 0)
        factors = diagnosis_data.get('contributing_factors', []) or diagnosis_data.get('factors', [])
        
        diagnosis = f"""
## {color} Failure Type: **{failure_type or 'Healthy'}**

### 🔍 Root Cause Analysis
{root_cause}

### 📊 Confidence: **{confidence}%**

### 📝 Contributing Factors
{chr(10).join(f'- {f}' for f in factors) if factors else '- None identified'}
"""
        
        proposal = result.get("proposal", {})
        fix = proposal.get("fix_command", "") or proposal.get("fix_yaml", "")
        risk_level = proposal.get("risk_level", "unknown")
        
        if fix:
            diagnosis += f"\n### ⚠️ Risk Level: **{risk_level.upper()}**\n"
        
        return diagnosis, fix, action_id, "✅ Diagnosis complete!", json.dumps(result, indent=2)
    except Exception as e:
        logger.exception("Diagnosis failed")
        error_msg = f"❌ **Error**: {str(e)}\n\nCheck:\n- kubectl is configured\n- Resource exists in cluster\n- OPENROUTER_API_KEY is set"
        return error_msg, "", "", f"Error: {str(e)}", ""


def approve_ui(action_id: str, execute: bool):
    """Approve and execute fix."""
    if action_id not in pending_actions:
        return f"❌ Error: Action {action_id} not found. Run diagnosis first."
    
    result = pending_actions[action_id]
    
    if not execute:
        return f"✅ Action {action_id} approved. Check 'Execute Fix' and click again to apply."
    
    # Execute the fix
    try:
        namespace = result.get("namespace", "default")
        resource_type = result.get("resource_type")
        resource_name = result.get("resource_name")
        
        if not resource_type or not resource_name:
            return f"❌ Error: Missing resource information in action {action_id}"
        
        agent = SREAgent()
        execution_result = agent.execute_fix(namespace, resource_type, resource_name)
        
        if "error" in execution_result:
            return f"❌ Execution failed: {execution_result['error']}"
        
        eval_result = execution_result.get("evaluation", {})
        if eval_result.get("fixed"):
            return f"✅ **Fix executed successfully!**\n\nStatus: {eval_result.get('status', 'healthy')}\n\nThe issue should now be resolved. Check the cluster to verify."
        else:
            return f"⚠️ **Fix executed but issue persists**\n\nStatus: {eval_result.get('status', 'unknown')}\n\nYou may need to investigate further or try a different approach."
    except Exception as e:
        logger.exception("Execution failed")
        return f"❌ **Error executing fix**: {str(e)}\n\nCheck logs for details."


def view_scenarios():
    """View test scenarios with current cluster status."""
    import subprocess
    from pathlib import Path
    
    scenarios_md = """
## 📋 Test Scenarios

### Scenario A: OOMKilled Pod

Three variants that will cause pods to be OOMKilled:

"""
    
    # Check cluster status
    try:
        # Check deployments
        result = subprocess.run(
            ["kubectl", "get", "deployments", "-n", "default", "-o", "json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            import json
            deployments = json.loads(result.stdout)
            oom_deployments = [d for d in deployments.get("items", []) if "oom-app" in d["metadata"]["name"]]
            
            scenarios_md += "#### Current Cluster Status:\n\n"
            if oom_deployments:
                scenarios_md += "✅ **Deployments Found:**\n"
                for dep in oom_deployments:
                    name = dep["metadata"]["name"]
                    ready = dep["status"].get("readyReplicas", 0)
                    replicas = dep["spec"]["replicas"]
                    scenarios_md += f"- `{name}`: {ready}/{replicas} ready\n"
            else:
                scenarios_md += "⚠️ **No OOM deployments found** - Deploy scenarios first!\n"
            
            # Check pods
            pod_result = subprocess.run(
                ["kubectl", "get", "pods", "-n", "default", "-o", "json"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if pod_result.returncode == 0:
                pods = json.loads(pod_result.stdout)
                oom_pods = [p for p in pods.get("items", []) if "oom-app" in p["metadata"]["name"]]
                if oom_pods:
                    scenarios_md += "\n**Pod Status:**\n"
                    for pod in oom_pods[:5]:  # Show first 5
                        name = pod["metadata"]["name"]
                        phase = pod["status"]["phase"]
                        reason = ""
                        if pod["status"].get("containerStatuses"):
                            cs = pod["status"]["containerStatuses"][0]
                            if cs.get("lastState", {}).get("terminated", {}).get("reason"):
                                reason = f" ({cs['lastState']['terminated']['reason']})"
                        scenarios_md += f"- `{name}`: {phase}{reason}\n"
        else:
            scenarios_md += "⚠️ **Cannot connect to cluster** - Check kubectl configuration\n"
    except Exception as e:
        scenarios_md += f"⚠️ **Error checking cluster**: {str(e)}\n"
    
    scenarios_md += """
#### Variants:

1. **Variant 1** (`variant_1_memory_limit_low.yaml`): 
   - Memory limit: 64Mi
   - Container tries to use 100M
   - **Status**: Will OOMKill immediately

2. **Variant 2** (`variant_2_memory_leak.yaml`):
   - Memory limit: 128Mi  
   - Gradual memory leak
   - **Status**: Will OOMKill after memory leak

3. **Variant 3** (`variant_3_jvm_heap.yaml`):
   - Memory limit: 200Mi
   - Stress test exceeds limit
   - **Status**: Will OOMKill when limit exceeded

#### Deploy Commands:
```shell
# Deploy all variants
./scripts/deploy_scenarios.sh

# Or deploy individually:
kubectl apply -f tests/scenarios/scenario_a_oom/variant_1_memory_limit_low.yaml
kubectl apply -f tests/scenarios/scenario_a_oom/variant_2_memory_leak.yaml
kubectl apply -f tests/scenarios/scenario_a_oom/variant_3_jvm_heap.yaml
```

---

### Scenario B: Broken Service

Service with label mismatch - pods are healthy but service has no endpoints.

"""
    
    # Check service status
    try:
        svc_result = subprocess.run(
            ["kubectl", "get", "svc", "broken-service", "-n", "default", "-o", "json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if svc_result.returncode == 0:
            import json
            svc = json.loads(svc_result.stdout)
            scenarios_md += "✅ **Service Found:** `broken-service`\n\n"
            
            # Check endpoints
            ep_result = subprocess.run(
                ["kubectl", "get", "endpoints", "broken-service", "-n", "default", "-o", "json"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if ep_result.returncode == 0:
                ep = json.loads(ep_result.stdout)
                subsets = ep.get("subsets", [])
                if subsets:
                    addresses = sum(len(s.get("addresses", [])) for s in subsets)
                    scenarios_md += f"**Endpoints**: {addresses} address(es) found\n"
                else:
                    scenarios_md += "**Endpoints**: ⚠️ **0 endpoints** (label mismatch detected!)\n"
            else:
                scenarios_md += "**Endpoints**: ⚠️ **0 endpoints** (label mismatch)\n"
        else:
            scenarios_md += "⚠️ **Service not found** - Deploy scenario first!\n"
    except Exception as e:
        scenarios_md += f"⚠️ **Error checking service**: {str(e)}\n"
    
    scenarios_md += """
#### Issue:
- **Deployment**: `healthy-app` has labels: `app=healthy-app, tier=backend`
- **Service**: `broken-service` selector looks for: `app=healthy-app, tier=frontend`
- **Result**: Service has 0 endpoints even though pods are healthy

#### Deploy Command:
```shell
kubectl apply -f tests/scenarios/scenario_b_service/broken_service.yaml
```

#### Verify:
```shell
# Check service has no endpoints
kubectl get endpoints broken-service

# Check pods are healthy
kubectl get pods -l app=healthy-app
```

---

### Quick Actions

**Deploy All Scenarios:**
```shell
./scripts/deploy_scenarios.sh
```

**Cleanup All Scenarios:**
```shell
./scripts/cleanup_scenarios.sh
```

**Test the Agent:**
- Use the **Diagnose** tab above
- For Scenario A: `namespace=default`, `resource_type=Deployment`, `resource_name=oom-app-v1`
- For Scenario B: `namespace=default`, `resource_type=Service`, `resource_name=broken-service`
"""
    
    return scenarios_md


def create_app():
    """Create Gradio app."""
    with gr.Blocks(title="Kubernetes SRE Agent") as app:
        gr.Markdown("# 🔍 Kubernetes SRE AI Agent")
        gr.Markdown("### Detect, diagnose, and remediate Kubernetes failures with AI")
        gr.Markdown("**Quick Start**: Go to **Test Scenarios** tab to see available scenarios, then use **Diagnose** tab to test them.")
        
        with gr.Tab("Diagnose"):
            with gr.Row():
                with gr.Column():
                    namespace = gr.Textbox(label="Namespace", value="default")
                    resource_type = gr.Dropdown(
                        label="Resource Type",
                        choices=["Deployment", "Service"],
                        value="Deployment"
                    )
                    resource_name = gr.Textbox(
                        label="Resource Name", 
                        placeholder="e.g., oom-app-v1 or broken-service",
                        info="For Scenario A: oom-app-v1, oom-app-v2, oom-app-v3\nFor Scenario B: broken-service"
                    )
                    diagnose_btn = gr.Button("🔍 Diagnose", variant="primary")
                
                with gr.Column():
                    diagnosis_output = gr.Markdown(label="Diagnosis Result", value="👆 Fill in the fields above and click 'Diagnose' to start")
                    proposed_fix = gr.Code(label="Proposed Fix (kubectl command or YAML)", language="shell", value="# Proposed fix will appear here after diagnosis")
                    action_id = gr.Textbox(label="Action ID", interactive=False, value="")
                    status = gr.Textbox(label="Status", value="Ready")
                    full_result = gr.JSON(label="Full Result", visible=False)
            
            diagnose_btn.click(
                diagnose_ui,
                inputs=[namespace, resource_type, resource_name],
                outputs=[diagnosis_output, proposed_fix, action_id, status, full_result]
            )
        
        with gr.Tab("Approve/Execute"):
            with gr.Row():
                with gr.Column():
                    action_id_input = gr.Textbox(label="Action ID")
                    execute = gr.Checkbox(label="Execute Fix", value=False)
                    approve_btn = gr.Button("✅ Approve & Execute", variant="primary")
                
                with gr.Column():
                    result = gr.Textbox(label="Result", lines=5)
            
            approve_btn.click(
                approve_ui,
                inputs=[action_id_input, execute],
                outputs=[result]
            )
        
        with gr.Tab("Test Scenarios"):
            scenarios = gr.Markdown(value=view_scenarios(), label="Scenarios")
            refresh_btn = gr.Button("🔄 Refresh Scenarios", variant="secondary")
            
            refresh_btn.click(
                view_scenarios,
                outputs=[scenarios]
            )
    
    return app


if __name__ == "__main__":
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860)
