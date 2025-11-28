"""FastAPI REST API for SRE Agent."""

import asyncio
import os
import secrets
from typing import Any

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from k8s_sre_agent.core.agent import SREAgent
from k8s_sre_agent.utils.logging import get_logger

logger = get_logger(__name__)

# Security: API Key authentication
API_KEY = os.getenv("API_SECRET_KEY", secrets.token_urlsafe(32))
security = HTTPBearer(auto_error=False)

# Rate limiting (simple in-memory)
from collections import defaultdict
from time import time
rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_REQUESTS = 100  # requests per window
RATE_LIMIT_WINDOW = 60  # seconds

# In-memory state store for pending approvals
pending_states: dict[str, dict[str, Any]] = {}


class DiagnoseRequest(BaseModel):
    namespace: str = "default"
    resource_type: str
    resource_name: str


class ApprovalRequest(BaseModel):
    workflow_id: str
    approved: bool


def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """Verify API key from Authorization header."""
    if not credentials:
        return False
    return credentials.credentials == API_KEY


def check_rate_limit(client_id: str = "default") -> bool:
    """Simple rate limiting."""
    now = time()
    # Clean old entries
    rate_limit_store[client_id] = [
        t for t in rate_limit_store[client_id] if now - t < RATE_LIMIT_WINDOW
    ]
    
    if len(rate_limit_store[client_id]) >= RATE_LIMIT_REQUESTS:
        return False
    
    rate_limit_store[client_id].append(now)
    return True


def create_app() -> FastAPI:
    app = FastAPI(
        title="K8s SRE Agent API",
        description="Kubernetes SRE AI Agent for failure detection and remediation",
        version="0.1.0",
    )
    
    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:7860", "http://localhost:3000", "http://127.0.0.1:7860"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint (no auth required)."""
        return {"status": "healthy"}
    
    @app.post("/diagnose")
    async def diagnose(
        req: DiagnoseRequest,
        authorized: bool = Depends(verify_api_key),
        x_forwarded_for: str = Header(None, alias="X-Forwarded-For")
    ) -> dict[str, Any]:
        """Diagnose a K8s resource and return action plan."""
        # Check authentication
        if not authorized:
            raise HTTPException(status_code=401, detail="API key required. Set Authorization: Bearer <API_KEY>")
        
        # Rate limiting
        client_id = x_forwarded_for or "default"
        if not check_rate_limit(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
        
        # Input validation
        if not req.resource_type or not req.resource_name:
            raise HTTPException(status_code=400, detail="resource_type and resource_name are required")
        
        if req.resource_type not in ["Deployment", "Service"]:
            raise HTTPException(status_code=400, detail="resource_type must be 'Deployment' or 'Service'")
        
        try:
            # Run synchronous agent code in thread pool to avoid async/dspy conflicts
            def run_diagnose():
                agent = SREAgent()
                return agent.run_until_approval(req.namespace, req.resource_type, req.resource_name)
            
            result = await asyncio.to_thread(run_diagnose)
            
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
    async def approve(
        req: ApprovalRequest,
        authorized: bool = Depends(verify_api_key),
        x_forwarded_for: str = Header(None, alias="X-Forwarded-For")
    ) -> dict[str, Any]:
        """Approve or reject a remediation action."""
        # Check authentication
        if not authorized:
            raise HTTPException(status_code=401, detail="API key required. Set Authorization: Bearer <API_KEY>")
        
        # Rate limiting
        client_id = x_forwarded_for or "default"
        if not check_rate_limit(client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
        
        if req.workflow_id not in pending_states:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        try:
            state = pending_states[req.workflow_id]
            
            # Run synchronous agent code in thread pool to avoid async/dspy conflicts
            def run_approve():
                agent = SREAgent()
                return agent.resume_with_approval(state, req.approved)
            
            result = await asyncio.to_thread(run_approve)
            
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
    async def list_pending(
        authorized: bool = Depends(verify_api_key)
    ) -> dict[str, Any]:
        """List pending approval workflows."""
        if not authorized:
            raise HTTPException(status_code=401, detail="API key required. Set Authorization: Bearer <API_KEY>")
        
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
    
    @app.get("/api-key")
    async def get_api_key() -> dict[str, str]:
        """Get API key for authentication (development only)."""
        return {
            "api_key": API_KEY,
            "warning": "This endpoint should be disabled in production",
            "usage": "Set Authorization header: Bearer <api_key>"
        }
    
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

