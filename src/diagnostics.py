"""
Diagnostic functions for analyzing Kubernetes issues.
"""
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Diagnostics:
    """Diagnostic functions for common Kubernetes issues."""
    
    @staticmethod
    def diagnose_oomkilled_pod(pod_status: Dict[str, Any], deployment_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Diagnose OOMKilled pod issues.
        
        Returns:
            Dictionary with diagnosis results including root cause and suggested fix.
        """
        diagnosis = {
            'issue_detected': False,
            'issue_type': 'OOMKilled',
            'root_cause': '',
            'details': {},
            'suggested_fix': {}
        }
        
        # Check container statuses for OOMKilled
        for container in pod_status.get('container_statuses', []):
            last_state = container.get('last_state', {})
            current_state = container.get('state', {})
            
            # Check if container was terminated due to OOM
            if last_state and last_state.get('state') == 'terminated':
                if last_state.get('reason') == 'OOMKilled':
                    diagnosis['issue_detected'] = True
                    diagnosis['details']['container_name'] = container['name']
                    diagnosis['details']['restart_count'] = container['restart_count']
                    
                    # Get current resource limits from deployment
                    container_spec = next(
                        (c for c in deployment_info['containers'] if c['name'] == container['name']),
                        None
                    )
                    
                    if container_spec:
                        current_memory_limit = container_spec['resources']['limits'].get('memory', 'Not set')
                        current_memory_request = container_spec['resources']['requests'].get('memory', 'Not set')
                        
                        diagnosis['root_cause'] = (
                            f"Container '{container['name']}' is being killed due to exceeding memory limits. "
                            f"Current memory limit: {current_memory_limit}, "
                            f"Current memory request: {current_memory_request}. "
                            f"The container has been restarted {container['restart_count']} times."
                        )
                        
                        # Suggest increasing memory limit
                        diagnosis['suggested_fix'] = {
                            'action': 'increase_memory_limit',
                            'deployment_name': deployment_info['name'],
                            'namespace': deployment_info['namespace'],
                            'container_name': container['name'],
                            'current_limit': current_memory_limit,
                            'suggested_limit': Diagnostics._calculate_new_memory_limit(current_memory_limit),
                            'patch': Diagnostics._generate_memory_patch(
                                container['name'],
                                Diagnostics._calculate_new_memory_limit(current_memory_limit)
                            )
                        }
                    break
        
        return diagnosis
    
    @staticmethod
    def diagnose_service_endpoints(service_info: Dict[str, Any], 
                                   endpoints_info: Dict[str, Any],
                                   pods_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Diagnose service endpoint issues, particularly label mismatches.
        
        Returns:
            Dictionary with diagnosis results including root cause and suggested fix.
        """
        diagnosis = {
            'issue_detected': False,
            'issue_type': 'ServiceEndpointMismatch',
            'root_cause': '',
            'details': {},
            'suggested_fix': {}
        }
        
        # Check if service has no endpoints
        has_endpoints = False
        for subset in endpoints_info.get('subsets', []):
            if subset.get('addresses'):
                has_endpoints = True
                break
        
        if not has_endpoints and pods_info:
            # Service has no endpoints but pods exist
            diagnosis['issue_detected'] = True
            
            service_selector = service_info.get('selector', {})
            pod_labels_list = [pod.get('labels', {}) for pod in pods_info]
            
            # Find mismatched labels
            mismatched_labels = {}
            matching_labels = {}
            
            for selector_key, selector_value in service_selector.items():
                matches = all(
                    pod_labels.get(selector_key) == selector_value
                    for pod_labels in pod_labels_list
                )
                if not matches:
                    # Find what values the pods actually have
                    pod_values = set(
                        pod_labels.get(selector_key, 'NOT_SET')
                        for pod_labels in pod_labels_list
                    )
                    mismatched_labels[selector_key] = {
                        'service_value': selector_value,
                        'pod_values': list(pod_values)
                    }
                else:
                    matching_labels[selector_key] = selector_value
            
            diagnosis['root_cause'] = (
                f"Service '{service_info['name']}' has no active endpoints because "
                f"its selector labels don't match the pod labels. "
                f"Mismatched labels: {mismatched_labels}. "
                f"Pods found: {len(pods_info)} but none match all selectors."
            )
            
            diagnosis['details'] = {
                'service_selector': service_selector,
                'mismatched_labels': mismatched_labels,
                'matching_labels': matching_labels,
                'pod_count': len(pods_info),
                'pod_labels': pod_labels_list
            }
            
            # Suggest fix: update service selector to match pod labels
            if mismatched_labels:
                # Use the pod labels as the correct values
                corrected_selector = matching_labels.copy()
                for label_key, values in mismatched_labels.items():
                    # Use the first pod's value for this label
                    if pod_labels_list and label_key in pod_labels_list[0]:
                        corrected_selector[label_key] = pod_labels_list[0][label_key]
                
                diagnosis['suggested_fix'] = {
                    'action': 'fix_service_selector',
                    'service_name': service_info['name'],
                    'namespace': service_info['namespace'],
                    'current_selector': service_selector,
                    'suggested_selector': corrected_selector,
                    'patch': {
                        'spec': {
                            'selector': corrected_selector
                        }
                    }
                }
        
        return diagnosis
    
    @staticmethod
    def _calculate_new_memory_limit(current_limit: str) -> str:
        """Calculate a new memory limit (increase by 3x for safety)."""
        if current_limit == 'Not set':
            return '256Mi'
        
        # Parse memory limit (assuming format like "50Mi", "1Gi", etc.)
        import re
        match = re.match(r'(\d+)([A-Za-z]+)', str(current_limit))
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            new_value = value * 3  # Increase by 3x
            return f"{new_value}{unit}"
        
        return '256Mi'  # Default fallback
    
    @staticmethod
    def _generate_memory_patch(container_name: str, new_limit: str) -> Dict[str, Any]:
        """Generate a patch for updating container memory limits."""
        return {
            'spec': {
                'template': {
                    'spec': {
                        'containers': [
                            {
                                'name': container_name,
                                'resources': {
                                    'limits': {
                                        'memory': new_limit
                                    },
                                    'requests': {
                                        'memory': new_limit
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
