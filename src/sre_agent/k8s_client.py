"""Kubernetes client for resource inspection."""

from typing import Any

from kubernetes import client, config

from sre_agent.utils import get_logger

logger = get_logger(__name__)


class K8sClient:
    """Simple Kubernetes client."""
    
    def __init__(self):
        """Initialize K8s client."""
        try:
            config.load_kube_config()
        except:
            try:
                config.load_incluster_config()
            except Exception as e:
                logger.warning(f"Could not load kubeconfig: {e}")
        
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
    
    def get_resource_state(self, namespace: str, resource_type: str, resource_name: str) -> dict[str, Any]:
        """Get resource state."""
        state = {
            "namespace": namespace,
            "resource_type": resource_type,
            "resource_name": resource_name,
        }
        
        if resource_type == "Deployment":
            dep = self.apps_v1.read_namespaced_deployment(resource_name, namespace)
            state["spec"] = {
                "replicas": dep.spec.replicas,
                "containers": [
                    {
                        "name": c.name,
                        "resources": {
                            "limits": {k: v for k, v in (c.resources.limits or {}).items()},
                            "requests": {k: v for k, v in (c.resources.requests or {}).items()},
                        }
                    }
                    for c in dep.spec.template.spec.containers
                ]
            }
            state["status"] = {
                "available_replicas": dep.status.available_replicas,
                "ready_replicas": dep.status.ready_replicas,
            }
        
        elif resource_type == "Service":
            svc = self.core_v1.read_namespaced_service(resource_name, namespace)
            state["spec"] = {
                "selector": svc.spec.selector or {},
                "ports": [{"port": p.port, "targetPort": p.target_port} for p in svc.spec.ports or []]
            }
            
            try:
                endpoints = self.core_v1.read_namespaced_endpoints(resource_name, namespace)
                state["endpoints"] = {
                    "subsets": [
                        {
                            "addresses": len(subset.addresses or []),
                        }
                        for subset in endpoints.subsets or []
                    ]
                }
            except:
                state["endpoints"] = {"subsets": []}
            
            # Get pod labels for comparison
            pods = self.core_v1.list_namespaced_pod(namespace)
            state["pod_labels"] = [
                pod.metadata.labels for pod in pods.items 
                if pod.status.phase == "Running"
            ]
            
            # Check for label mismatch
            service_selector = svc.spec.selector or {}
            matching_pods = [
                pod for pod in pods.items
                if pod.status.phase == "Running"
                and all(pod.metadata.labels.get(k) == v for k, v in service_selector.items())
            ]
            state["matching_pods_count"] = len(matching_pods)
            state["label_mismatch"] = len(matching_pods) == 0 and len([p for p in pods.items if p.status.phase == "Running"]) > 0
        
        return state
    
    def has_oom_killed(self, namespace: str, deployment_name: str) -> bool:
        """Check if deployment has OOMKilled pods."""
        try:
            # Get deployment to find its selector labels
            dep = self.apps_v1.read_namespaced_deployment(deployment_name, namespace)
            selector = dep.spec.selector.match_labels
            
            # Build label selector string
            label_selector = ",".join([f"{k}={v}" for k, v in selector.items()])
            
            # Get pods matching deployment selector
            pods = self.core_v1.list_namespaced_pod(
                namespace,
                label_selector=label_selector
            )
            
            for pod in pods.items:
                # Check container statuses
                for container in pod.status.container_statuses or []:
                    # Check last state (terminated)
                    if container.last_state and container.last_state.terminated:
                        if container.last_state.terminated.reason == "OOMKilled":
                            logger.info(f"Found OOMKilled pod: {pod.metadata.name}")
                            return True
                    # Check current state (if currently terminated)
                    if container.state and container.state.terminated:
                        if container.state.terminated.reason == "OOMKilled":
                            logger.info(f"Found OOMKilled pod (current): {pod.metadata.name}")
                            return True
        except Exception as e:
            logger.error(f"Error checking OOMKilled: {e}")
        return False
    
    def has_endpoints(self, namespace: str, service_name: str) -> bool:
        """Check if service has endpoints."""
        try:
            endpoints = self.core_v1.read_namespaced_endpoints(service_name, namespace)
            return any(
                len(subset.addresses or []) > 0
                for subset in endpoints.subsets or []
            )
        except:
            return False

