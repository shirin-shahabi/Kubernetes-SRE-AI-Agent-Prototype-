"""Gradio UI for human-in-the-loop SRE Agent."""

import json
import os
from datetime import datetime

import gradio as gr

from k8s_sre_agent.core.agent import SREAgent
from k8s_sre_agent.utils.logging import get_logger

logger = get_logger(__name__)

pending_actions: dict[str, dict] = {}
feedback_history: list[dict] = []


def check_api_key():
    """Check if API key is set."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return False, "❌ OPENROUTER_API_KEY not set! Please export it:\nexport OPENROUTER_API_KEY='your-key'"
    return True, "✅ API key configured"


def diagnose(namespace: str, resource_type: str, resource_name: str):
    """Run diagnosis and return results."""
    # Check API key first
    key_ok, key_msg = check_api_key()
    if not key_ok:
        return f"**❌ Error:** {key_msg}", "", "", ""
    
    # Validate inputs
    if not namespace or not namespace.strip():
        return "**❌ Error:** Namespace is required", "", "", ""
    if not resource_type or not resource_type.strip():
        return "**❌ Error:** Resource Type is required", "", "", ""
    if not resource_name or not resource_name.strip():
        return "**❌ Error:** Resource Name is required", "", "", ""
    
    try:
        agent = SREAgent()
        result = agent.run_until_approval(namespace, resource_type, resource_name)
        
        workflow_id = result.get("workflow_id", "")
        
        if not workflow_id:
            return "**❌ Error:** No workflow ID returned. Check logs for details.", "", "", ""
        
        pending_actions[workflow_id] = result
        
        # Check if failure was detected
        if not result.get("detected"):
            diagnosis_md = f"""
## ✅ No Failure Detected

The resource `{resource_name}` appears to be healthy.

**Status:** No issues found
**Resource Type:** {resource_type}
**Namespace:** {namespace}
"""
            return diagnosis_md, "No fix needed - resource is healthy", workflow_id, json.dumps(result, indent=2)
        
        diagnosis = result.get("diagnosis", {})
        steps = result.get("action_steps", [])
        
        diagnosis_md = f"""
## Failure: {result.get('failure_type', 'Unknown')}

### Root Cause
{diagnosis.get('root_cause', 'N/A')}

### Confidence: {diagnosis.get('confidence', 0)}%

### Workflow ID
**{workflow_id}**

⚠️ **Copy this Workflow ID to use in the "Approve & Execute" tab!**
"""
        
        fix_cmd = steps[0]["command"] if steps else "No fix available"
        
        return diagnosis_md, fix_cmd, workflow_id, json.dumps(result, indent=2)
    
    except ValueError as e:
        error_msg = str(e)
        if "OPENROUTER_API_KEY" in error_msg:
            return f"**❌ Error:** {error_msg}\n\nPlease set: export OPENROUTER_API_KEY='your-key'", "", "", ""
        return f"**❌ Error:** {error_msg}", "", "", ""
    except Exception as e:
        logger.exception("diagnosis_failed")
        error_str = str(e)
        # Provide helpful error messages
        if "connection" in error_str.lower() or "timeout" in error_str.lower():
            return f"**❌ Connection Error:** {error_str}\n\nCheck:\n- Kubernetes cluster is accessible\n- kubectl works: `kubectl get nodes`", "", "", ""
        elif "not found" in error_str.lower():
            return f"**❌ Resource Not Found:** {error_str}\n\nCheck:\n- Resource name: `{resource_name}`\n- Namespace: `{namespace}`\n- Resource exists: `kubectl get {resource_type.lower()} {resource_name} -n {namespace}`", "", "", ""
        else:
            return f"**❌ Error:** {error_str}\n\nCheck the terminal where UI is running for detailed logs.", "", "", ""


def approve_action(workflow_id: str, execute: bool, feedback: str):
    """Approve and optionally execute the fix."""
    # Check API key first
    key_ok, key_msg = check_api_key()
    if not key_ok:
        return f"**Error:** {key_msg}", get_feedback_log()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if not workflow_id or workflow_id.strip() == "":
        return "❌ Please enter a Workflow ID from the Diagnose tab.", get_feedback_log()
    
    # Check if user might have pasted a pod name instead
    if workflow_id.startswith("oom-test-app") or workflow_id.startswith("broken-svc-app"):
        return f"""❌ **Error: You pasted a pod name, not a Workflow ID!**

You pasted: `{workflow_id}`

**What to do:**
1. Go back to the **"Diagnose"** tab
2. Run diagnosis again
3. Look for the **"Workflow ID"** field (it's a UUID like `abc123-def456-7890-...`)
4. Copy that complete Workflow ID
5. Paste it here (NOT the pod name)

The Workflow ID is shown in the Diagnose tab after you click "Diagnose".""", get_feedback_log()
    
    if workflow_id not in pending_actions:
        return f"""❌ Workflow '{workflow_id[:20]}...' not found.

**Possible reasons:**
1. You didn't run diagnosis first - Go to "Diagnose" tab and click "Diagnose"
2. You copied the wrong ID - Make sure it's the Workflow ID (UUID), not pod name
3. You ran diagnosis in a different session - Run diagnosis again

**What a Workflow ID looks like:** `abc123-def456-7890-ghij-klmnopqrstuv`
**What it's NOT:** `oom-test-app-7dcdbf9bfc-l48cx` (that's a pod name)""", get_feedback_log()
    
    state = pending_actions[workflow_id]
    failure_type = state.get("failure_type", "Unknown")
    
    if not execute:
        feedback_history.append({
            "time": timestamp,
            "workflow": workflow_id[:8],
            "action": "approved_no_execute",
            "failure": failure_type,
            "feedback": feedback or "Approved but not executed",
        })
        return "✅ Action approved but NOT executed. Check 'Execute Fix' to apply changes.", get_feedback_log()
    
    try:
        agent = SREAgent()
        result = agent.resume_with_approval(pending_actions[workflow_id], approved=True)
        
        eval_result = result.get("evaluation", {})
        success = eval_result.get("fixed", False)
        
        feedback_history.append({
            "time": timestamp,
            "workflow": workflow_id[:8],
            "action": "approved_and_executed",
            "failure": failure_type,
            "feedback": feedback or "No feedback provided",
            "result": "success" if success else "partial",
        })
        
        del pending_actions[workflow_id]
        
        if success:
            msg = f"""✅ FIX APPLIED SUCCESSFULLY

Status: {eval_result.get('status', 'healthy')}
Pattern stored in knowledge base for future reference.

Your feedback: {feedback or 'None'}"""
        else:
            msg = f"""⚠️ Fix applied but issue may persist

Status: {eval_result.get('status', 'unknown')}
Please verify manually.

Your feedback: {feedback or 'None'}"""
        
        return msg, get_feedback_log()
    
    except Exception as e:
        feedback_history.append({
            "time": timestamp,
            "workflow": workflow_id[:8],
            "action": "execution_failed",
            "failure": failure_type,
            "feedback": feedback or "None",
            "error": str(e),
        })
        return f"❌ Execution failed: {e}", get_feedback_log()


def get_feedback_log():
    """Get formatted feedback history."""
    if not feedback_history:
        return "No feedback recorded yet. Approve actions to see history here."
    
    log = "### Human Feedback History\n\n"
    log += "| Time | Workflow | Action | Failure | Result |\n"
    log += "|------|----------|--------|---------|--------|\n"
    
    for entry in feedback_history[-10:]:  # Last 10 entries
        result = entry.get("result", entry.get("error", "-"))
        log += f"| {entry['time']} | {entry['workflow']} | {entry['action']} | {entry['failure']} | {result[:30]} |\n"
    
    return log


def create_app() -> gr.Blocks:
    """Create Gradio app."""
    # Check API key on startup
    key_ok, key_msg = check_api_key()
    
    with gr.Blocks(title="K8s SRE Agent") as app:
        gr.Markdown("# K8s SRE AI Agent")
        gr.Markdown("Detect, diagnose, and remediate Kubernetes failures")
        
        # Show API key status
        if not key_ok:
            gr.Markdown(f"### ⚠️ Configuration Issue\n{key_msg}", elem_classes="warning")
        else:
            gr.Markdown(f"### {key_msg}", elem_classes="success")
        
        with gr.Tab("Diagnose"):
            with gr.Row():
                with gr.Column():
                    ns_input = gr.Textbox(label="Namespace", value="default")
                    type_input = gr.Dropdown(
                        label="Resource Type",
                        choices=["Deployment", "Service"],
                        value="Deployment"
                    )
                    name_input = gr.Textbox(label="Resource Name", placeholder="my-app")
                    diagnose_btn = gr.Button("Diagnose", variant="primary")
                
                with gr.Column():
                    diagnosis_out = gr.Markdown(label="Diagnosis")
                    fix_out = gr.Code(label="Proposed Fix", language="shell")
                    wf_id = gr.Textbox(
                        label="Workflow ID (Copy this!)",
                        interactive=False,
                        info="⚠️ Copy this complete Workflow ID to use in the 'Approve & Execute' tab"
                    )
                    raw_out = gr.JSON(label="Raw Result", visible=False)
            
            diagnose_btn.click(
                diagnose,
                inputs=[ns_input, type_input, name_input],
                outputs=[diagnosis_out, fix_out, wf_id, raw_out]
            )
        
        with gr.Tab("Approve & Execute"):
            gr.Markdown("### Human-in-the-Loop: Review and Approve Fixes")
            gr.Markdown("The agent waits for your approval before executing any changes.")
            gr.Markdown("**⚠️ IMPORTANT:** Use the **Workflow ID** from the Diagnose tab (looks like `abc123-def456-7890-...`), NOT the pod name!")
            
            with gr.Row():
                with gr.Column():
                    wf_input = gr.Textbox(
                        label="Workflow ID (from Diagnose tab)",
                        placeholder="Paste Workflow ID here (e.g., abc123-def456-7890-ghij-klmnopqrstuv)",
                        info="This is the UUID shown in the Diagnose tab, NOT the pod name"
                    )
                    exec_check = gr.Checkbox(
                        label="✅ Execute Fix (uncheck to approve only)",
                        value=False
                    )
                    feedback_input = gr.Textbox(
                        label="Your Feedback (optional)",
                        placeholder="Add notes, concerns, or reason for approval...",
                        lines=3
                    )
                    approve_btn = gr.Button("Submit Approval", variant="primary", size="lg")
                
                with gr.Column():
                    result_out = gr.Markdown(label="Execution Result")
            
            gr.Markdown("---")
            feedback_log_out = gr.Markdown(label="Feedback History", value=get_feedback_log())
            
            approve_btn.click(
                approve_action,
                inputs=[wf_input, exec_check, feedback_input],
                outputs=[result_out, feedback_log_out]
            )
        
        with gr.Tab("Scenarios"):
            gr.Markdown("""
## Test Scenarios

### Scenario A: OOMKilled Pod
Deploy: `kubectl apply -f tests/scenarios/oom_killed/memory_limit_low.yaml`

### Scenario B: Broken Service  
Deploy: `kubectl apply -f tests/scenarios/broken_service/label_mismatch.yaml`
""")
    
    return app


if __name__ == "__main__":
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860)

