"""Simple Kubernetes client for resource inspection and execution."""

import subprocess
from typing import Any

from kubernetes import client, config as k8s_config

from k8s_sre_agent.utils.config import get_config
from k8s_sre_agent.utils.logging import get_logger

logger = get_logger(__name__)


class K8sClient:
    """Kubernetes client for resource inspection and safe command execution."""
    
    def __init__(self) -> None:
        try:
            k8s_config.load_kube_config()
        except Exception:
            try:
                k8s_config.load_incluster_config()
            except Exception as e:
                logger.warning("kubeconfig_load_failed", error=str(e))
        
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.config = get_config()
    
    def get_resource_state(
        self, namespace: str, resource_type: str, resource_name: str
    ) -> dict[str, Any]:
        """Get current state of a K8s resource."""
        state = {
            "namespace": namespace,
            "resource_type": resource_type,
            "resource_name": resource_name,
        }
        
        try:
            if resource_type == "Deployment":
                dep = self.apps_v1.read_namespaced_deployment(resource_name, namespace)
                state["spec"] = {
                    "replicas": dep.spec.replicas,
                    "containers": [
                        {
                            "name": c.name,
                            "resources": {
                                "limits": dict(c.resources.limits or {}),
                                "requests": dict(c.resources.requests or {}),
                            }
                        }
                        for c in dep.spec.template.spec.containers
                    ]
                }
                state["status"] = {
                    "available": dep.status.available_replicas,
                    "ready": dep.status.ready_replicas,
                }
            
            elif resource_type == "Service":
                svc = self.core_v1.read_namespaced_service(resource_name, namespace)
                state["spec"] = {
                    "selector": svc.spec.selector or {},
                    "ports": [{"port": p.port, "targetPort": p.target_port} for p in svc.spec.ports or []],
                }
                
                try:
                    eps = self.core_v1.read_namespaced_endpoints(resource_name, namespace)
                    state["endpoints"] = {"subsets": [
                        {"addresses": len(s.addresses or [])} for s in eps.subsets or []
                    ]}
                except Exception:
                    state["endpoints"] = {"subsets": []}
                
                pods = self.core_v1.list_namespaced_pod(namespace)
                state["pod_labels"] = [
                    p.metadata.labels for p in pods.items if p.status.phase == "Running"
                ]
        
        except Exception as e:
            logger.error("get_state_failed", error=str(e))
            state["error"] = str(e)
        
        return state
    
    def has_oom_killed(self, namespace: str, deployment_name: str) -> bool:
        """Check if deployment has OOMKilled pods."""
        try:
            pods = self.core_v1.list_namespaced_pod(namespace, label_selector=f"app={deployment_name}")
            for pod in pods.items:
                for cs in pod.status.container_statuses or []:
                    if cs.last_state and cs.last_state.terminated:
                        if cs.last_state.terminated.reason == "OOMKilled":
                            return True
        except Exception:
            pass
        return False
    
    def has_endpoints(self, namespace: str, service_name: str) -> bool:
        """Check if service has active endpoints."""
        try:
            eps = self.core_v1.read_namespaced_endpoints(service_name, namespace)
            return any(len(s.addresses or []) > 0 for s in eps.subsets or [])
        except Exception:
            return False
    
    def execute(self, command: str, dry_run: bool = False) -> dict[str, Any]:
        """Execute a kubectl command safely."""
        if dry_run:
            command = f"{command} --dry-run=client"
        
        # Check for dangerous commands
        dangerous = self.config.get("safety", {}).get("dangerous_commands", [])
        for pattern in dangerous:
            if pattern in command and not dry_run:
                return {"success": False, "error": f"Blocked dangerous command: {pattern}"}
        
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=60
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "dry_run": dry_run,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

