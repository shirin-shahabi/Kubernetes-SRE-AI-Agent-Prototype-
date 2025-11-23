"""
Kubernetes client wrapper for interacting with the cluster.
"""
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class KubernetesClient:
    """Wrapper for Kubernetes API client operations."""
    
    def __init__(self):
        """Initialize Kubernetes client using kubeconfig or in-cluster config."""
        try:
            config.load_kube_config()
            logger.info("Loaded kubeconfig")
        except Exception:
            try:
                config.load_incluster_config()
                logger.info("Loaded in-cluster config")
            except Exception as e:
                logger.error(f"Failed to load Kubernetes config: {e}")
                raise
        
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
    
    def get_pod_status(self, namespace: str, pod_name: str) -> Dict[str, Any]:
        """Get detailed status of a specific pod."""
        try:
            pod = self.core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            return {
                'name': pod.metadata.name,
                'namespace': pod.metadata.namespace,
                'phase': pod.status.phase,
                'conditions': [
                    {'type': c.type, 'status': c.status, 'reason': c.reason}
                    for c in (pod.status.conditions or [])
                ],
                'container_statuses': [
                    {
                        'name': cs.name,
                        'ready': cs.ready,
                        'restart_count': cs.restart_count,
                        'state': self._get_container_state(cs.state),
                        'last_state': self._get_container_state(cs.last_state) if cs.last_state else None
                    }
                    for cs in (pod.status.container_statuses or [])
                ]
            }
        except ApiException as e:
            logger.error(f"Error getting pod status: {e}")
            raise
    
    def _get_container_state(self, state) -> Dict[str, Any]:
        """Extract container state information."""
        if state.running:
            return {'state': 'running', 'started_at': str(state.running.started_at)}
        elif state.waiting:
            return {'state': 'waiting', 'reason': state.waiting.reason, 'message': state.waiting.message}
        elif state.terminated:
            return {
                'state': 'terminated',
                'reason': state.terminated.reason,
                'exit_code': state.terminated.exit_code,
                'signal': state.terminated.signal,
                'message': state.terminated.message
            }
        return {'state': 'unknown'}
    
    def get_pods_by_label(self, namespace: str, label_selector: str) -> List[Dict[str, Any]]:
        """Get pods matching a label selector."""
        try:
            pods = self.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=label_selector
            )
            return [
                {
                    'name': pod.metadata.name,
                    'namespace': pod.metadata.namespace,
                    'phase': pod.status.phase,
                    'labels': pod.metadata.labels,
                    'container_statuses': [
                        {
                            'name': cs.name,
                            'ready': cs.ready,
                            'restart_count': cs.restart_count,
                            'state': self._get_container_state(cs.state),
                            'last_state': self._get_container_state(cs.last_state) if cs.last_state else None
                        }
                        for cs in (pod.status.container_statuses or [])
                    ] if pod.status.container_statuses else []
                }
                for pod in pods.items
            ]
        except ApiException as e:
            logger.error(f"Error listing pods: {e}")
            raise
    
    def get_deployment(self, namespace: str, deployment_name: str) -> Dict[str, Any]:
        """Get deployment details."""
        try:
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )
            return {
                'name': deployment.metadata.name,
                'namespace': deployment.metadata.namespace,
                'replicas': deployment.spec.replicas,
                'selector': deployment.spec.selector.match_labels,
                'template_labels': deployment.spec.template.metadata.labels,
                'containers': [
                    {
                        'name': c.name,
                        'image': c.image,
                        'resources': {
                            'requests': c.resources.requests if c.resources and c.resources.requests else {},
                            'limits': c.resources.limits if c.resources and c.resources.limits else {}
                        }
                    }
                    for c in deployment.spec.template.spec.containers
                ],
                'status': {
                    'available_replicas': deployment.status.available_replicas,
                    'ready_replicas': deployment.status.ready_replicas,
                    'replicas': deployment.status.replicas
                }
            }
        except ApiException as e:
            logger.error(f"Error getting deployment: {e}")
            raise
    
    def get_service(self, namespace: str, service_name: str) -> Dict[str, Any]:
        """Get service details."""
        try:
            service = self.core_v1.read_namespaced_service(
                name=service_name,
                namespace=namespace
            )
            return {
                'name': service.metadata.name,
                'namespace': service.metadata.namespace,
                'selector': service.spec.selector,
                'ports': [
                    {
                        'port': p.port,
                        'target_port': str(p.target_port),
                        'protocol': p.protocol
                    }
                    for p in service.spec.ports
                ],
                'type': service.spec.type
            }
        except ApiException as e:
            logger.error(f"Error getting service: {e}")
            raise
    
    def get_endpoints(self, namespace: str, service_name: str) -> Dict[str, Any]:
        """Get endpoints for a service."""
        try:
            endpoints = self.core_v1.read_namespaced_endpoints(
                name=service_name,
                namespace=namespace
            )
            return {
                'name': endpoints.metadata.name,
                'namespace': endpoints.metadata.namespace,
                'subsets': [
                    {
                        'addresses': [{'ip': addr.ip, 'target_ref': addr.target_ref.name if addr.target_ref else None}
                                     for addr in (subset.addresses or [])],
                        'not_ready_addresses': [{'ip': addr.ip} for addr in (subset.not_ready_addresses or [])],
                        'ports': [{'port': p.port, 'protocol': p.protocol} for p in (subset.ports or [])]
                    }
                    for subset in (endpoints.subsets or [])
                ]
            }
        except ApiException as e:
            logger.error(f"Error getting endpoints: {e}")
            raise
    
    def patch_deployment(self, namespace: str, deployment_name: str, patch_body: Dict[str, Any]) -> bool:
        """Patch a deployment with the provided changes."""
        try:
            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=patch_body
            )
            logger.info(f"Successfully patched deployment {deployment_name}")
            return True
        except ApiException as e:
            logger.error(f"Error patching deployment: {e}")
            raise
    
    def patch_service(self, namespace: str, service_name: str, patch_body: Dict[str, Any]) -> bool:
        """Patch a service with the provided changes."""
        try:
            self.core_v1.patch_namespaced_service(
                name=service_name,
                namespace=namespace,
                body=patch_body
            )
            logger.info(f"Successfully patched service {service_name}")
            return True
        except ApiException as e:
            logger.error(f"Error patching service: {e}")
            raise
