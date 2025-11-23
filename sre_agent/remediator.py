"""
Remediation module for fixing Kubernetes issues
"""
import logging
from typing import Dict, Any, List, Callable
from enum import Enum

from .detector import Issue, FailureType

logger = logging.getLogger(__name__)


class RemediationAction(Enum):
    """Types of remediation actions"""
    RESTART_POD = "restart_pod"
    RESTART_DEPLOYMENT = "restart_deployment"
    SCALE_DEPLOYMENT = "scale_deployment"
    DELETE_POD = "delete_pod"
    NO_ACTION = "no_action"
    MANUAL_INTERVENTION = "manual_intervention"


class RemediationPlan:
    """Represents a plan to remediate an issue"""
    
    def __init__(self, issue: Issue, action: RemediationAction,
                 parameters: Dict[str, Any], justification: str,
                 risk_level: str = "low"):
        self.issue = issue
        self.action = action
        self.parameters = parameters
        self.justification = justification
        self.risk_level = risk_level
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary"""
        return {
            "issue": self.issue.to_dict(),
            "action": self.action.value,
            "parameters": self.parameters,
            "justification": self.justification,
            "risk_level": self.risk_level
        }
    
    def __str__(self) -> str:
        return (
            f"Remediation Plan: {self.action.value} for {self.issue.resource_name} "
            f"(risk: {self.risk_level})\n"
            f"Justification: {self.justification}"
        )


class Remediator:
    """Handles remediation of Kubernetes issues"""
    
    def __init__(self, k8s_client, dry_run: bool = True):
        """
        Initialize the remediator
        
        Args:
            k8s_client: KubernetesClient instance
            dry_run: Whether to run in dry-run mode
        """
        self.k8s_client = k8s_client
        self.dry_run = dry_run
        
        # Map failure types to remediation strategies
        self.remediation_strategies = {
            FailureType.POD_CRASH_LOOP: self._handle_crash_loop,
            FailureType.POD_IMAGE_PULL_ERROR: self._handle_image_pull_error,
            FailureType.POD_OOM_KILLED: self._handle_oom_killed,
            FailureType.POD_PENDING: self._handle_pending_pod,
            FailureType.DEPLOYMENT_UNAVAILABLE: self._handle_deployment_unavailable,
            FailureType.HIGH_RESTART_COUNT: self._handle_high_restart_count,
        }
    
    def create_remediation_plan(self, issue: Issue, 
                               diagnosis: Dict[str, Any]) -> RemediationPlan:
        """
        Create a remediation plan based on the issue and diagnosis
        
        Args:
            issue: The detected issue
            diagnosis: The diagnosis from the diagnostician
            
        Returns:
            RemediationPlan
        """
        logger.info(f"Creating remediation plan for: {issue}")
        
        # Get the appropriate strategy
        strategy = self.remediation_strategies.get(
            issue.failure_type,
            self._handle_unknown
        )
        
        # Execute strategy to get plan
        plan = strategy(issue, diagnosis)
        
        logger.info(f"Created plan: {plan.action.value}")
        return plan
    
    def execute_plan(self, plan: RemediationPlan) -> Dict[str, Any]:
        """
        Execute a remediation plan
        
        Args:
            plan: The remediation plan to execute
            
        Returns:
            Result dictionary with success status and details
        """
        logger.info(f"Executing remediation plan: {plan.action.value}")
        
        if plan.action == RemediationAction.NO_ACTION:
            return {
                "success": True,
                "action": plan.action.value,
                "message": "No action required"
            }
        
        if plan.action == RemediationAction.MANUAL_INTERVENTION:
            return {
                "success": False,
                "action": plan.action.value,
                "message": "Manual intervention required",
                "details": plan.justification
            }
        
        # Execute the action
        try:
            if plan.action == RemediationAction.DELETE_POD:
                success = self.k8s_client.delete_pod(
                    pod_name=plan.parameters["pod_name"],
                    namespace=plan.parameters["namespace"],
                    dry_run=self.dry_run
                )
            
            elif plan.action == RemediationAction.RESTART_DEPLOYMENT:
                success = self.k8s_client.restart_deployment(
                    deployment_name=plan.parameters["deployment_name"],
                    namespace=plan.parameters["namespace"],
                    dry_run=self.dry_run
                )
            
            elif plan.action == RemediationAction.SCALE_DEPLOYMENT:
                success = self.k8s_client.scale_deployment(
                    deployment_name=plan.parameters["deployment_name"],
                    replicas=plan.parameters["replicas"],
                    namespace=plan.parameters["namespace"],
                    dry_run=self.dry_run
                )
            
            else:
                return {
                    "success": False,
                    "action": plan.action.value,
                    "message": f"Unknown action: {plan.action.value}"
                }
            
            result = {
                "success": success,
                "action": plan.action.value,
                "message": "Action executed successfully" if success else "Action failed",
                "dry_run": self.dry_run,
                "parameters": plan.parameters
            }
            
            logger.info(f"Remediation result: {result['message']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute remediation: {e}")
            return {
                "success": False,
                "action": plan.action.value,
                "message": f"Execution failed: {str(e)}"
            }
    
    def _handle_crash_loop(self, issue: Issue, diagnosis: Dict[str, Any]) -> RemediationPlan:
        """Handle CrashLoopBackOff"""
        # Crash loops typically need manual investigation, but we can try deleting the pod
        return RemediationPlan(
            issue=issue,
            action=RemediationAction.DELETE_POD,
            parameters={
                "pod_name": issue.resource_name,
                "namespace": issue.namespace
            },
            justification=(
                f"Pod is in CrashLoopBackOff. Deleting pod to force recreation. "
                f"Root cause: {diagnosis.get('root_cause', 'Unknown')}"
            ),
            risk_level="low"
        )
    
    def _handle_image_pull_error(self, issue: Issue, diagnosis: Dict[str, Any]) -> RemediationPlan:
        """Handle image pull errors"""
        # Image pull errors usually require manual intervention
        return RemediationPlan(
            issue=issue,
            action=RemediationAction.MANUAL_INTERVENTION,
            parameters={},
            justification=(
                f"Image pull error detected. This typically requires checking: "
                f"1) Image name and tag are correct, "
                f"2) Image exists in registry, "
                f"3) Registry credentials are valid. "
                f"Root cause: {diagnosis.get('root_cause', 'Unknown')}"
            ),
            risk_level="low"
        )
    
    def _handle_oom_killed(self, issue: Issue, diagnosis: Dict[str, Any]) -> RemediationPlan:
        """Handle OOMKilled containers"""
        # OOM requires resource adjustment, which is risky to automate
        return RemediationPlan(
            issue=issue,
            action=RemediationAction.MANUAL_INTERVENTION,
            parameters={},
            justification=(
                f"Container killed due to out-of-memory. "
                f"Recommendation: Increase memory limits in deployment spec. "
                f"Root cause: {diagnosis.get('root_cause', 'Insufficient memory')}"
            ),
            risk_level="medium"
        )
    
    def _handle_pending_pod(self, issue: Issue, diagnosis: Dict[str, Any]) -> RemediationPlan:
        """Handle pending pods"""
        # Pending pods usually need resource or scheduling fixes
        return RemediationPlan(
            issue=issue,
            action=RemediationAction.MANUAL_INTERVENTION,
            parameters={},
            justification=(
                f"Pod stuck in pending state. "
                f"Check for: insufficient cluster resources, node selectors, "
                f"taints/tolerations, or PVC issues. "
                f"Root cause: {diagnosis.get('root_cause', 'Unknown')}"
            ),
            risk_level="low"
        )
    
    def _handle_deployment_unavailable(self, issue: Issue, diagnosis: Dict[str, Any]) -> RemediationPlan:
        """Handle unavailable deployments"""
        # Try restarting the deployment
        return RemediationPlan(
            issue=issue,
            action=RemediationAction.RESTART_DEPLOYMENT,
            parameters={
                "deployment_name": issue.resource_name,
                "namespace": issue.namespace
            },
            justification=(
                f"Deployment has unavailable replicas. Attempting restart. "
                f"Root cause: {diagnosis.get('root_cause', 'Unknown')}"
            ),
            risk_level="medium"
        )
    
    def _handle_high_restart_count(self, issue: Issue, diagnosis: Dict[str, Any]) -> RemediationPlan:
        """Handle high restart counts"""
        restart_count = issue.details.get("restart_count", 0)
        
        if restart_count > 10:
            # Very high restart count - manual intervention needed
            return RemediationPlan(
                issue=issue,
                action=RemediationAction.MANUAL_INTERVENTION,
                parameters={},
                justification=(
                    f"Pod has {restart_count} restarts. "
                    f"This indicates a persistent issue requiring investigation. "
                    f"Root cause: {diagnosis.get('root_cause', 'Unknown')}"
                ),
                risk_level="medium"
            )
        else:
            # Moderate restart count - try deleting pod
            return RemediationPlan(
                issue=issue,
                action=RemediationAction.DELETE_POD,
                parameters={
                    "pod_name": issue.resource_name,
                    "namespace": issue.namespace
                },
                justification=(
                    f"Pod has {restart_count} restarts. Deleting to force clean restart. "
                    f"Root cause: {diagnosis.get('root_cause', 'Unknown')}"
                ),
                risk_level="low"
            )
    
    def _handle_unknown(self, issue: Issue, diagnosis: Dict[str, Any]) -> RemediationPlan:
        """Handle unknown issues"""
        return RemediationPlan(
            issue=issue,
            action=RemediationAction.MANUAL_INTERVENTION,
            parameters={},
            justification=(
                f"Unknown issue type. Manual investigation required. "
                f"Root cause: {diagnosis.get('root_cause', 'Unknown')}"
            ),
            risk_level="unknown"
        )
