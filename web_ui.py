#!/usr/bin/env python3
"""
Gradio Web UI for the SRE AI Agent with human-in-the-loop approval.
"""
import gradio as gr
import logging
import os
from dotenv import load_dotenv

from src.orchestrator import SREOrchestrator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize orchestrator
try:
    orchestrator = SREOrchestrator(openai_api_key=os.getenv('OPENAI_API_KEY'))
except Exception as e:
    logger.error(f"Failed to initialize orchestrator: {e}")
    orchestrator = None


def diagnose_oomkilled(namespace: str, deployment: str):
    """Diagnose OOMKilled scenario."""
    if not orchestrator:
        return "❌ Error: Orchestrator not initialized. Check Kubernetes configuration.", ""
    
    if not deployment:
        return "❌ Error: Deployment name is required", ""
    
    try:
        result = orchestrator.diagnose_oomkilled_scenario(namespace, deployment)
        
        if not result.get('success'):
            return f"❌ Error: {result.get('error')}", ""
        
        diagnosis = result.get('diagnosis', {})
        
        # Format diagnosis output
        output = f"""
🔍 **DIAGNOSIS RESULTS - OOMKilled Pod**

**Issue Type:** {diagnosis.get('issue_type', 'N/A')}

**Root Cause:**
{diagnosis.get('root_cause', 'N/A')}

**AI Analysis:**
{result.get('ai_analysis', 'N/A')}
        """
        
        # Format suggested fix
        suggested_fix = diagnosis.get('suggested_fix', {})
        fix_output = f"""
🛠️ **PROPOSED REMEDIATION**

**Action:** Increase Memory Limit
**Deployment:** {suggested_fix.get('deployment_name')}
**Namespace:** {namespace}
**Container:** {suggested_fix.get('container_name')}
**Current Limit:** {suggested_fix.get('current_limit')}
**Proposed Limit:** {suggested_fix.get('suggested_limit')}
        """
        
        return output, fix_output
    
    except Exception as e:
        logger.error(f"Error during diagnosis: {e}")
        return f"❌ Error: {str(e)}", ""


def diagnose_broken_service(namespace: str, service: str):
    """Diagnose broken service scenario."""
    if not orchestrator:
        return "❌ Error: Orchestrator not initialized. Check Kubernetes configuration.", ""
    
    if not service:
        return "❌ Error: Service name is required", ""
    
    try:
        result = orchestrator.diagnose_broken_service_scenario(namespace, service)
        
        if not result.get('success'):
            return f"❌ Error: {result.get('error')}", ""
        
        diagnosis = result.get('diagnosis', {})
        
        # Format diagnosis output
        output = f"""
🔍 **DIAGNOSIS RESULTS - Broken Service**

**Issue Type:** {diagnosis.get('issue_type', 'N/A')}

**Root Cause:**
{diagnosis.get('root_cause', 'N/A')}

**AI Analysis:**
{result.get('ai_analysis', 'N/A')}
        """
        
        # Format suggested fix
        suggested_fix = diagnosis.get('suggested_fix', {})
        fix_output = f"""
🛠️ **PROPOSED REMEDIATION**

**Action:** Fix Service Selector
**Service:** {suggested_fix.get('service_name')}
**Namespace:** {namespace}
**Current Selector:** {suggested_fix.get('current_selector')}
**Proposed Selector:** {suggested_fix.get('suggested_selector')}
        """
        
        return output, fix_output
    
    except Exception as e:
        logger.error(f"Error during diagnosis: {e}")
        return f"❌ Error: {str(e)}", ""


def run_diagnosis(scenario: str, namespace: str, resource_name: str):
    """Run diagnosis based on selected scenario."""
    if scenario == "OOMKilled Pod":
        result = orchestrator.diagnose_oomkilled_scenario(namespace, resource_name)
    else:  # Broken Service
        result = orchestrator.diagnose_broken_service_scenario(namespace, resource_name)
    
    if not result.get('success'):
        return f"❌ Error: {result.get('error')}", "", gr.update(visible=False), None
    
    diagnosis = result.get('diagnosis', {})
    
    # Format diagnosis
    diagnosis_text = f"""
🔍 **DIAGNOSIS RESULTS**

**Scenario:** {result.get('scenario')}

**Root Cause:**
{diagnosis.get('root_cause', 'N/A')}

**AI Analysis:**
{result.get('ai_analysis', 'N/A')}
    """
    
    # Format remediation
    suggested_fix = diagnosis.get('suggested_fix', {})
    action = suggested_fix.get('action', 'Unknown')
    
    if action == 'increase_memory_limit':
        remediation_text = f"""
🛠️ **PROPOSED REMEDIATION**

**Action:** Increase Memory Limit
**Deployment:** {suggested_fix.get('deployment_name')}
**Container:** {suggested_fix.get('container_name')}
**Current Limit:** {suggested_fix.get('current_limit')}
**Proposed Limit:** {suggested_fix.get('suggested_limit')}
        """
    elif action == 'fix_service_selector':
        remediation_text = f"""
🛠️ **PROPOSED REMEDIATION**

**Action:** Fix Service Selector
**Service:** {suggested_fix.get('service_name')}
**Current Selector:** {suggested_fix.get('current_selector')}
**Proposed Selector:** {suggested_fix.get('suggested_selector')}
        """
    else:
        remediation_text = f"**Action:** {action}"
    
    return diagnosis_text, remediation_text, gr.update(visible=True), result


def execute_fix(diagnosis_result):
    """Execute the approved remediation."""
    if not diagnosis_result:
        return "❌ No diagnosis result available. Please run diagnosis first."
    
    try:
        execution_result = orchestrator.execute_remediation(diagnosis_result)
        
        if execution_result.get('success'):
            return f"""
✅ **REMEDIATION EXECUTED SUCCESSFULLY**

{execution_result.get('message')}

**Action:** {execution_result.get('action')}

**Next Steps:**
Please verify the fix:
- For OOMKilled: Check pod status with `kubectl get pods`
- For Broken Service: Check endpoints with `kubectl get endpoints`
            """
        else:
            return f"❌ **REMEDIATION FAILED**\n\n{execution_result.get('error')}"
    
    except Exception as e:
        logger.error(f"Error executing remediation: {e}")
        return f"❌ Error: {str(e)}"


def create_ui():
    """Create the Gradio UI."""
    with gr.Blocks(title="Kubernetes SRE AI Agent", theme=gr.themes.Soft()) as app:
        gr.Markdown("""
        # 🤖 Kubernetes SRE AI Agent
        
        Diagnose and remediate common Kubernetes issues with AI-powered analysis.
        
        **Supported Scenarios:**
        - **Scenario A:** OOMKilled Pod - Detect and fix memory limit issues
        - **Scenario B:** Broken Service - Detect and fix service label mismatches
        """)
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("## 1️⃣ Configure Diagnosis")
                
                scenario = gr.Radio(
                    choices=["OOMKilled Pod", "Broken Service"],
                    label="Select Scenario",
                    value="OOMKilled Pod"
                )
                
                namespace = gr.Textbox(
                    label="Namespace",
                    value="default",
                    placeholder="default"
                )
                
                resource_name = gr.Textbox(
                    label="Resource Name (Deployment or Service)",
                    placeholder="e.g., oom-app or broken-service"
                )
                
                diagnose_btn = gr.Button("🔍 Run Diagnosis", variant="primary", size="lg")
            
            with gr.Column():
                gr.Markdown("## 2️⃣ Review Results")
                
                diagnosis_output = gr.Markdown(label="Diagnosis Results")
                
                remediation_output = gr.Markdown(label="Proposed Remediation")
        
        with gr.Row(visible=False) as approval_row:
            with gr.Column():
                gr.Markdown("## 3️⃣ Human Approval Required")
                gr.Markdown("⚠️ Review the proposed remediation above and approve to execute the fix.")
                
                with gr.Row():
                    approve_btn = gr.Button("✅ Approve & Execute", variant="primary", size="lg")
                    reject_btn = gr.Button("⛔ Reject", variant="stop", size="lg")
        
        execution_output = gr.Markdown(label="Execution Results")
        
        # State to store diagnosis result (thread-safe per-session)
        diagnosis_state = gr.State(value=None)
        
        # Event handlers
        diagnose_btn.click(
            fn=run_diagnosis,
            inputs=[scenario, namespace, resource_name],
            outputs=[diagnosis_output, remediation_output, approval_row, diagnosis_state]
        )
        
        approve_btn.click(
            fn=execute_fix,
            inputs=[diagnosis_state],
            outputs=[execution_output]
        )
        
        reject_btn.click(
            fn=lambda: "⛔ Remediation rejected by operator. No changes made.",
            outputs=[execution_output]
        )
        
        gr.Markdown("""
        ---
        ### 📚 Instructions
        
        1. **Select a scenario** and provide the namespace and resource name
        2. **Click "Run Diagnosis"** to analyze the issue
        3. **Review the AI analysis** and proposed remediation
        4. **Approve or reject** the suggested fix
        5. **Verify the fix** using kubectl commands shown in the results
        
        ### 🔧 Prerequisites
        
        - Valid kubeconfig with cluster access
        - OpenAI API key set in `.env` file (optional, for enhanced AI analysis)
        - Test scenarios deployed in your cluster
        """)
    
    return app


if __name__ == "__main__":
    if not orchestrator:
        print("❌ Failed to initialize orchestrator. Please check your Kubernetes configuration.")
        print("Ensure you have a valid kubeconfig and access to a Kubernetes cluster.")
        exit(1)
    
    app = create_ui()
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)
