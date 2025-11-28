"""FastAPI REST API for SRE Agent."""

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from k8s_sre_agent.core.agent import SREAgent
from k8s_sre_agent.utils.logging import get_logger

logger = get_logger(__name__)

# In-memory state store for pending approvals
pending_states: dict[str, dict[str, Any]] = {}


class DiagnoseRequest(BaseModel):
    namespace: str = "default"
    resource_type: str
    resource_name: str


class ApprovalRequest(BaseModel):
    workflow_id: str
    approved: bool


def create_app() -> FastAPI:
    app = FastAPI(
        title="K8s SRE Agent API",
        description="Kubernetes SRE AI Agent for failure detection and remediation",
        version="0.1.0",
    )
    
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy"}
    
    @app.post("/diagnose")
    async def diagnose(req: DiagnoseRequest) -> dict[str, Any]:
        """Diagnose a K8s resource and return action plan."""
        try:
            agent = SREAgent()
            result = agent.run_until_approval(req.namespace, req.resource_type, req.resource_name)
            
            workflow_id = result.get("workflow_id", "")
            pending_states[workflow_id] = result
            
            return {
                "workflow_id": workflow_id,
                "detected": result.get("detected"),
                "failure_type": result.get("failure_type"),
                "diagnosis": result.get("diagnosis"),
                "action_steps": result.get("action_steps"),
                "approval_status": result.get("approval_status"),
            }
        except Exception as e:
            logger.error("diagnose_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/approve")
    async def approve(req: ApprovalRequest) -> dict[str, Any]:
        """Approve or reject a remediation action."""
        if req.workflow_id not in pending_states:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        try:
            state = pending_states[req.workflow_id]
            agent = SREAgent()
            result = agent.resume_with_approval(state, req.approved)
            
            del pending_states[req.workflow_id]
            
            return {
                "workflow_id": req.workflow_id,
                "approved": req.approved,
                "execution_result": result.get("execution_result"),
                "evaluation": result.get("evaluation"),
            }
        except Exception as e:
            logger.error("approve_failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/pending")
    async def list_pending() -> dict[str, Any]:
        """List pending approval workflows."""
        return {
            "pending": [
                {
                    "workflow_id": wid,
                    "resource": f"{s['namespace']}/{s['resource_type']}/{s['resource_name']}",
                    "failure_type": s.get("failure_type"),
                }
                for wid, s in pending_states.items()
            ]
        }
    
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

