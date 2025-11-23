"""
Main orchestrator for the SRE AI Agent.
"""
from typing import Dict, Any, Optional
import logging
from src.k8s_client import KubernetesClient
from src.diagnostics import Diagnostics
from src.agent import SREAgent

logger = logging.getLogger(__name__)


class SREOrchestrator:
    """Main orchestrator that coordinates diagnosis and remediation."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize the orchestrator with required components."""
        self.k8s_client = KubernetesClient()
        self.diagnostics = Diagnostics()
        self.agent = SREAgent(openai_api_key)
        logger.info("SRE Orchestrator initialized")
    
    def diagnose_oomkilled_scenario(self, namespace: str, deployment_name: str) -> Dict[str, Any]:
        """
        Diagnose Scenario A: OOMKilled Pod
        
        Args:
            namespace: Kubernetes namespace
            deployment_name: Name of the deployment with OOMKilled pod
            
        Returns:
            Dictionary with diagnosis and remediation information
        """
        logger.info(f"Diagnosing OOMKilled scenario for deployment {deployment_name}")
        
        # Get deployment info
        deployment_info = self.k8s_client.get_deployment(namespace, deployment_name)
        
        # Get pods for this deployment
        selector_labels = deployment_info['selector']
        label_selector = ','.join([f"{k}={v}" for k, v in selector_labels.items()])
        pods = self.k8s_client.get_pods_by_label(namespace, label_selector)
        
        if not pods:
            return {
                'success': False,
                'error': 'No pods found for deployment'
            }
        
        # Analyze the most recent pod (likely the one with issues)
        pod = pods[0]
        
        # Run diagnostics
        diagnosis = self.diagnostics.diagnose_oomkilled_pod(pod, deployment_info)
        
        if not diagnosis['issue_detected']:
            return {
                'success': False,
                'error': 'No OOMKilled issue detected in the pods'
            }
        
        # Get AI analysis
        ai_analysis = self.agent.analyze_diagnosis(diagnosis)
        
        return {
            'success': True,
            'scenario': 'OOMKilled Pod',
            'deployment': deployment_name,
            'namespace': namespace,
            'diagnosis': diagnosis,
            'ai_analysis': ai_analysis,
            'remediation_ready': True
        }
    
    def diagnose_broken_service_scenario(self, namespace: str, service_name: str) -> Dict[str, Any]:
        """
        Diagnose Scenario B: Broken Service (label mismatch)
        
        Args:
            namespace: Kubernetes namespace
            service_name: Name of the service with endpoint issues
            
        Returns:
            Dictionary with diagnosis and remediation information
        """
        logger.info(f"Diagnosing broken service scenario for service {service_name}")
        
        # Get service info
        service_info = self.k8s_client.get_service(namespace, service_name)
        
        # Get endpoints
        endpoints_info = self.k8s_client.get_endpoints(namespace, service_name)
        
        # Get pods that should be selected by this service
        # First, try to find pods with partial label match
        selector_labels = service_info.get('selector', {})
        if not selector_labels:
            return {
                'success': False,
                'error': 'Service has no selector labels'
            }
        
        # Get all pods in namespace and filter
        all_pods_response = self.k8s_client.core_v1.list_namespaced_pod(namespace=namespace)
        
        # Find pods that match at least one selector label
        candidate_pods = []
        for pod in all_pods_response.items:
            pod_labels = pod.metadata.labels or {}
            # Check if any selector label matches
            if any(pod_labels.get(k) == v for k, v in selector_labels.items()):
                candidate_pods.append({
                    'name': pod.metadata.name,
                    'namespace': pod.metadata.namespace,
                    'phase': pod.status.phase,
                    'labels': pod_labels
                })
        
        if not candidate_pods:
            return {
                'success': False,
                'error': 'No candidate pods found that could match the service'
            }
        
        # Run diagnostics
        diagnosis = self.diagnostics.diagnose_service_endpoints(
            service_info,
            endpoints_info,
            candidate_pods
        )
        
        if not diagnosis['issue_detected']:
            return {
                'success': False,
                'error': 'No service endpoint issue detected'
            }
        
        # Get AI analysis
        ai_analysis = self.agent.analyze_diagnosis(diagnosis)
        
        return {
            'success': True,
            'scenario': 'Broken Service',
            'service': service_name,
            'namespace': namespace,
            'diagnosis': diagnosis,
            'ai_analysis': ai_analysis,
            'remediation_ready': True
        }
    
    def execute_remediation(self, diagnosis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the remediation based on diagnosis.
        
        Args:
            diagnosis_result: Result from diagnose_* methods
            
        Returns:
            Dictionary with execution results
        """
        if not diagnosis_result.get('success') or not diagnosis_result.get('remediation_ready'):
            return {
                'success': False,
                'error': 'Invalid diagnosis result or remediation not ready'
            }
        
        diagnosis = diagnosis_result['diagnosis']
        suggested_fix = diagnosis.get('suggested_fix', {})
        
        if not suggested_fix:
            return {
                'success': False,
                'error': 'No suggested fix available'
            }
        
        action = suggested_fix.get('action')
        namespace = diagnosis_result['namespace']
        
        try:
            if action == 'increase_memory_limit':
                deployment_name = suggested_fix['deployment_name']
                patch = suggested_fix['patch']
                
                self.k8s_client.patch_deployment(namespace, deployment_name, patch)
                
                return {
                    'success': True,
                    'action': action,
                    'message': f"Successfully increased memory limit for deployment {deployment_name}",
                    'details': suggested_fix
                }
            
            elif action == 'fix_service_selector':
                service_name = suggested_fix['service_name']
                patch = suggested_fix['patch']
                
                self.k8s_client.patch_service(namespace, service_name, patch)
                
                return {
                    'success': True,
                    'action': action,
                    'message': f"Successfully fixed service selector for {service_name}",
                    'details': suggested_fix
                }
            
            else:
                return {
                    'success': False,
                    'error': f"Unknown action: {action}"
                }
        
        except Exception as e:
            logger.error(f"Error executing remediation: {e}")
            return {
                'success': False,
                'error': str(e)
            }
