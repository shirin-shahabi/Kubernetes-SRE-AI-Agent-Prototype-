"""
Detection module for identifying Kubernetes failures
"""
import logging
from typing import List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of failures the agent can detect"""
    POD_CRASH_LOOP = "pod_crash_loop"
    POD_IMAGE_PULL_ERROR = "pod_image_pull_error"
    POD_OOM_KILLED = "pod_oom_killed"
    POD_PENDING = "pod_pending"
    DEPLOYMENT_UNAVAILABLE = "deployment_unavailable"
    HIGH_RESTART_COUNT = "high_restart_count"
    UNKNOWN = "unknown"


class Issue:
    """Represents a detected issue in the cluster"""
    
    def __init__(self, failure_type: FailureType, resource_type: str,
                 resource_name: str, namespace: str, details: Dict[str, Any]):
        self.failure_type = failure_type
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.namespace = namespace
        self.details = details
        self.severity = self._calculate_severity()
    
    def _calculate_severity(self) -> str:
        """Calculate issue severity based on type and details"""
        if self.failure_type in [FailureType.POD_OOM_KILLED, FailureType.DEPLOYMENT_UNAVAILABLE]:
            return "high"
        elif self.failure_type in [FailureType.POD_CRASH_LOOP, FailureType.HIGH_RESTART_COUNT]:
            return "medium"
        else:
            return "low"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert issue to dictionary"""
        return {
            "failure_type": self.failure_type.value,
            "resource_type": self.resource_type,
            "resource_name": self.resource_name,
            "namespace": self.namespace,
            "severity": self.severity,
            "details": self.details
        }
    
    def __str__(self) -> str:
        return (
            f"Issue: {self.failure_type.value} - "
            f"{self.resource_type}/{self.resource_name} "
            f"in {self.namespace} (severity: {self.severity})"
        )


class FailureDetector:
    """Detects common Kubernetes failures"""
    
    def __init__(self, k8s_client):
        """
        Initialize the failure detector
        
        Args:
            k8s_client: KubernetesClient instance
        """
        self.k8s_client = k8s_client
    
    def detect_issues(self, namespace: str = "default") -> List[Issue]:
        """
        Detect all issues in the cluster
        
        Args:
            namespace: Kubernetes namespace to check
            
        Returns:
            List of detected issues
        """
        issues = []
        
        # Detect pod-related issues
        pod_issues = self._detect_pod_issues(namespace)
        issues.extend(pod_issues)
        
        # Detect deployment issues
        deployment_issues = self._detect_deployment_issues(namespace)
        issues.extend(deployment_issues)
        
        logger.info(f"Detected {len(issues)} issues in namespace {namespace}")
        return issues
    
    def _detect_pod_issues(self, namespace: str) -> List[Issue]:
        """Detect pod-related issues"""
        issues = []
        pods = self.k8s_client.get_all_pods(namespace)
        
        for pod in pods:
            # Check for crash loops
            if pod["restart_count"] > 5:
                issues.append(Issue(
                    failure_type=FailureType.HIGH_RESTART_COUNT,
                    resource_type="Pod",
                    resource_name=pod["name"],
                    namespace=pod["namespace"],
                    details={
                        "restart_count": pod["restart_count"],
                        "status": pod["status"]
                    }
                ))
            
            # Check container statuses
            for container in pod.get("container_statuses", []):
                state = container.get("state", {})
                
                # Image pull errors
                if "waiting" in state:
                    waiting = state["waiting"]
                    if waiting.get("reason") in ["ImagePullBackOff", "ErrImagePull"]:
                        issues.append(Issue(
                            failure_type=FailureType.POD_IMAGE_PULL_ERROR,
                            resource_type="Pod",
                            resource_name=pod["name"],
                            namespace=pod["namespace"],
                            details={
                                "container": container["name"],
                                "reason": waiting.get("reason"),
                                "message": waiting.get("message")
                            }
                        ))
                    elif waiting.get("reason") == "CrashLoopBackOff":
                        issues.append(Issue(
                            failure_type=FailureType.POD_CRASH_LOOP,
                            resource_type="Pod",
                            resource_name=pod["name"],
                            namespace=pod["namespace"],
                            details={
                                "container": container["name"],
                                "restart_count": container["restart_count"],
                                "message": waiting.get("message")
                            }
                        ))
                
                # OOMKilled containers
                if "terminated" in state:
                    terminated = state["terminated"]
                    if terminated.get("reason") == "OOMKilled":
                        issues.append(Issue(
                            failure_type=FailureType.POD_OOM_KILLED,
                            resource_type="Pod",
                            resource_name=pod["name"],
                            namespace=pod["namespace"],
                            details={
                                "container": container["name"],
                                "exit_code": terminated.get("exit_code"),
                                "message": terminated.get("message")
                            }
                        ))
            
            # Check if pod is stuck in pending
            if pod["status"] == "Pending":
                # Check if it's been pending for a while
                for condition in pod.get("conditions", []):
                    if condition["type"] == "PodScheduled" and condition["status"] == "False":
                        issues.append(Issue(
                            failure_type=FailureType.POD_PENDING,
                            resource_type="Pod",
                            resource_name=pod["name"],
                            namespace=pod["namespace"],
                            details={
                                "reason": condition.get("reason"),
                                "status": pod["status"]
                            }
                        ))
        
        return issues
    
    def _detect_deployment_issues(self, namespace: str) -> List[Issue]:
        """Detect deployment-related issues"""
        issues = []
        deployments = self.k8s_client.get_deployments(namespace)
        
        for deploy in deployments:
            # Check if deployment has unavailable replicas
            if deploy["replicas"] > 0 and deploy["available_replicas"] < deploy["replicas"]:
                issues.append(Issue(
                    failure_type=FailureType.DEPLOYMENT_UNAVAILABLE,
                    resource_type="Deployment",
                    resource_name=deploy["name"],
                    namespace=deploy["namespace"],
                    details={
                        "desired_replicas": deploy["replicas"],
                        "available_replicas": deploy["available_replicas"],
                        "ready_replicas": deploy["ready_replicas"],
                        "unavailable_replicas": deploy.get("unavailable_replicas", 0)
                    }
                ))
        
        return issues
