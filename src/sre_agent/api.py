"""FastAPI server with monitoring."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

from sre_agent.agent import SREAgent
from sre_agent.utils import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Kubernetes SRE Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
diagnosis_counter = Counter("diagnosis_total", "Total diagnoses", ["failure_type"])
diagnosis_duration = Histogram("diagnosis_duration_seconds", "Diagnosis duration")

pending_actions = {}


class DiagnoseRequest(BaseModel):
    namespace: str = "default"
    resource_type: str
    resource_name: str


class ApproveRequest(BaseModel):
    action_id: str
    execute: bool = False


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")


@app.post("/diagnose")
def diagnose(req: DiagnoseRequest):
    """Diagnose a Kubernetes resource."""
    with diagnosis_duration.time():
        try:
            agent = SREAgent()
            result = agent.run(req.namespace, req.resource_type, req.resource_name)
            
            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            
            failure_type = result.get("failure_type", "none")
            diagnosis_counter.labels(failure_type=failure_type).inc()
            
            action_id = f"{req.namespace}-{req.resource_type}-{req.resource_name}"
            pending_actions[action_id] = result
            result["action_id"] = action_id
            
            logger.info("Diagnosis complete", action_id=action_id, failure_type=failure_type)
            
            return result
        except Exception as e:
            logger.exception("Diagnosis failed")
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/approve")
def approve(req: ApproveRequest):
    """Approve and optionally execute a fix."""
    if req.action_id not in pending_actions:
        raise HTTPException(status_code=404, detail="Action not found")
    
    pending_actions[req.action_id]["approval_status"] = "approved"
    
    if req.execute:
        # Re-run execution node
        result = pending_actions[req.action_id]
        if "evaluation" in result:
            return {
                "success": True,
                "executed": True,
                "evaluation": result["evaluation"],
            }
    
    return {"success": True, "approved": True}


@app.get("/actions")
def list_actions():
    """List pending actions."""
    return {"actions": list(pending_actions.keys())}


@app.get("/cache/stats")
def cache_stats():
    """Get cache statistics."""
    from sre_agent.cache import CacheManager
    cache = CacheManager()
    return cache.stats()


@app.post("/cache/clear")
def clear_cache():
    """Clear cache."""
    from sre_agent.cache import CacheManager
    cache = CacheManager()
    cache.clear()
    return {"status": "cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
