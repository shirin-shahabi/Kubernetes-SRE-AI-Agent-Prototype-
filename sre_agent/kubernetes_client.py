"""
Kubernetes interaction layer for the SRE AI Agent
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)


class KubernetesClient:
    """Wrapper for Kubernetes API interactions"""
    
    def __init__(self, kubeconfig_path: Optional[str] = None):
        """
        Initialize Kubernetes client
        
        Args:
            kubeconfig_path: Path to kubeconfig file (None for in-cluster config)
        """
        try:
            if kubeconfig_path:
                k8s_config.load_kube_config(config_file=kubeconfig_path)
            else:
                try:
                    k8s_config.load_incluster_config()
                except k8s_config.ConfigException:
                    k8s_config.load_kube_config()
            
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            logger.info("Kubernetes client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise
    
    def get_all_pods(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """
        Get all pods in a namespace
        
        Args:
            namespace: Kubernetes namespace
            
        Returns:
            List of pod information dictionaries
        """
        try:
            pods = self.v1.list_namespaced_pod(namespace)
            pod_list = []
            
            for pod in pods.items:
                pod_info = {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "status": pod.status.phase,
                    "restart_count": sum(
                        cs.restart_count for cs in pod.status.container_statuses or []
                    ),
                    "conditions": [
                        {"type": c.type, "status": c.status, "reason": c.reason}
                        for c in pod.status.conditions or []
                    ],
                    "container_statuses": []
                }
                
                if pod.status.container_statuses:
                    for cs in pod.status.container_statuses:
                        status_info = {
                            "name": cs.name,
                            "ready": cs.ready,
                            "restart_count": cs.restart_count,
                            "state": {}
                        }
                        
                        if cs.state.running:
                            status_info["state"]["running"] = True
                        elif cs.state.waiting:
                            status_info["state"]["waiting"] = {
                                "reason": cs.state.waiting.reason,
                                "message": cs.state.waiting.message
                            }
                        elif cs.state.terminated:
                            status_info["state"]["terminated"] = {
                                "reason": cs.state.terminated.reason,
                                "exit_code": cs.state.terminated.exit_code,
                                "message": cs.state.terminated.message
                            }
                        
                        pod_info["container_statuses"].append(status_info)
                
                pod_list.append(pod_info)
            
            return pod_list
        except ApiException as e:
            logger.error(f"Failed to get pods: {e}")
            return []
    
    def get_pod_logs(self, pod_name: str, namespace: str = "default", 
                     tail_lines: int = 50) -> str:
        """
        Get logs from a pod
        
        Args:
            pod_name: Name of the pod
            namespace: Kubernetes namespace
            tail_lines: Number of lines to retrieve
            
        Returns:
            Pod logs as string
        """
        try:
            logs = self.v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=tail_lines
            )
            return logs
        except ApiException as e:
            logger.error(f"Failed to get pod logs: {e}")
            return f"Error retrieving logs: {e}"
    
    def get_events(self, namespace: str = "default", 
                   field_selector: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get Kubernetes events
        
        Args:
            namespace: Kubernetes namespace
            field_selector: Field selector for filtering events
            
        Returns:
            List of event dictionaries
        """
        try:
            events = self.v1.list_namespaced_event(
                namespace=namespace,
                field_selector=field_selector
            )
            
            event_list = []
            for event in events.items:
                event_list.append({
                    "type": event.type,
                    "reason": event.reason,
                    "message": event.message,
                    "involved_object": {
                        "kind": event.involved_object.kind,
                        "name": event.involved_object.name
                    },
                    "count": event.count,
                    "first_timestamp": str(event.first_timestamp),
                    "last_timestamp": str(event.last_timestamp)
                })
            
            return event_list
        except ApiException as e:
            logger.error(f"Failed to get events: {e}")
            return []
    
    def get_deployments(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """
        Get all deployments in a namespace
        
        Args:
            namespace: Kubernetes namespace
            
        Returns:
            List of deployment information dictionaries
        """
        try:
            deployments = self.apps_v1.list_namespaced_deployment(namespace)
            deployment_list = []
            
            for deploy in deployments.items:
                deployment_list.append({
                    "name": deploy.metadata.name,
                    "namespace": deploy.metadata.namespace,
                    "replicas": deploy.spec.replicas,
                    "ready_replicas": deploy.status.ready_replicas or 0,
                    "available_replicas": deploy.status.available_replicas or 0,
                    "unavailable_replicas": deploy.status.unavailable_replicas or 0
                })
            
            return deployment_list
        except ApiException as e:
            logger.error(f"Failed to get deployments: {e}")
            return []
    
    def restart_deployment(self, deployment_name: str, namespace: str = "default",
                          dry_run: bool = True) -> bool:
        """
        Restart a deployment by updating its annotation
        
        Args:
            deployment_name: Name of the deployment
            namespace: Kubernetes namespace
            dry_run: Whether to perform dry-run
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if dry_run:
                logger.info(f"DRY RUN: Would restart deployment {deployment_name}")
                return True
            
            # Get the deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                deployment_name, namespace
            )
            
            # Update annotation to trigger restart
            if deployment.spec.template.metadata.annotations is None:
                deployment.spec.template.metadata.annotations = {}
            
            deployment.spec.template.metadata.annotations[
                "kubectl.kubernetes.io/restartedAt"
            ] = datetime.utcnow().isoformat()
            
            # Patch the deployment
            self.apps_v1.patch_namespaced_deployment(
                deployment_name, namespace, deployment
            )
            
            logger.info(f"Restarted deployment {deployment_name}")
            return True
        except ApiException as e:
            logger.error(f"Failed to restart deployment: {e}")
            return False
    
    def scale_deployment(self, deployment_name: str, replicas: int,
                        namespace: str = "default", dry_run: bool = True) -> bool:
        """
        Scale a deployment to specified replicas
        
        Args:
            deployment_name: Name of the deployment
            replicas: Number of replicas
            namespace: Kubernetes namespace
            dry_run: Whether to perform dry-run
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if dry_run:
                logger.info(
                    f"DRY RUN: Would scale deployment {deployment_name} "
                    f"to {replicas} replicas"
                )
                return True
            
            # Scale the deployment
            self.apps_v1.patch_namespaced_deployment_scale(
                deployment_name,
                namespace,
                {"spec": {"replicas": replicas}}
            )
            
            logger.info(f"Scaled deployment {deployment_name} to {replicas} replicas")
            return True
        except ApiException as e:
            logger.error(f"Failed to scale deployment: {e}")
            return False
    
    def delete_pod(self, pod_name: str, namespace: str = "default",
                   dry_run: bool = True) -> bool:
        """
        Delete a pod (for forcing recreation)
        
        Args:
            pod_name: Name of the pod
            namespace: Kubernetes namespace
            dry_run: Whether to perform dry-run
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if dry_run:
                logger.info(f"DRY RUN: Would delete pod {pod_name}")
                return True
            
            self.v1.delete_namespaced_pod(pod_name, namespace)
            logger.info(f"Deleted pod {pod_name}")
            return True
        except ApiException as e:
            logger.error(f"Failed to delete pod: {e}")
            return False
