"""
Main SRE AI Agent orchestration
"""
import logging
import time
from typing import List, Dict, Any, Optional

from .config import AgentConfig
from .kubernetes_client import KubernetesClient
from .detector import FailureDetector, Issue
from .diagnostician import Diagnostician
from .remediator import Remediator, RemediationPlan

logger = logging.getLogger(__name__)


class SREAgent:
    """Main SRE AI Agent that orchestrates detection, diagnosis, and remediation"""
    
    def __init__(self, config: AgentConfig):
        """
        Initialize the SRE Agent
        
        Args:
            config: Agent configuration
        """
        self.config = config
        
        # Initialize components
        logger.info("Initializing SRE Agent components...")
        
        self.k8s_client = KubernetesClient(config.kubeconfig_path)
        self.detector = FailureDetector(self.k8s_client)
        self.diagnostician = Diagnostician(config.openai_api_key)
        self.remediator = Remediator(self.k8s_client, dry_run=config.dry_run)
        
        # Tracking
        self.remediation_history: List[Dict[str, Any]] = []
        
        logger.info("SRE Agent initialized successfully")
    
    def run_once(self, namespace: str = "default") -> Dict[str, Any]:
        """
        Run a single detection-diagnosis-remediation cycle
        
        Args:
            namespace: Kubernetes namespace to monitor
            
        Returns:
            Summary of actions taken
        """
        logger.info(f"Starting SRE cycle for namespace: {namespace}")
        
        summary = {
            "timestamp": time.time(),
            "namespace": namespace,
            "issues_detected": 0,
            "issues_diagnosed": 0,
            "remediations_attempted": 0,
            "remediations_successful": 0,
            "issues": [],
            "actions": []
        }
        
        try:
            # Step 1: Detect issues
            issues = self.detector.detect_issues(namespace)
            summary["issues_detected"] = len(issues)
            
            if not issues:
                logger.info("No issues detected")
                return summary
            
            logger.info(f"Detected {len(issues)} issues")
            
            # Step 2: Diagnose and remediate each issue
            for issue in issues:
                issue_result = self._process_issue(issue, namespace)
                summary["issues"].append(issue_result)
                
                if issue_result.get("diagnosed"):
                    summary["issues_diagnosed"] += 1
                
                if issue_result.get("remediation_attempted"):
                    summary["remediations_attempted"] += 1
                    
                    if issue_result.get("remediation_result", {}).get("success"):
                        summary["remediations_successful"] += 1
                
                summary["actions"].append(issue_result)
            
            logger.info(
                f"Cycle complete: {summary['issues_detected']} detected, "
                f"{summary['remediations_attempted']} remediations attempted, "
                f"{summary['remediations_successful']} successful"
            )
            
        except Exception as e:
            logger.error(f"Error during SRE cycle: {e}")
            summary["error"] = str(e)
        
        return summary
    
    def _process_issue(self, issue: Issue, namespace: str) -> Dict[str, Any]:
        """
        Process a single issue through diagnosis and remediation
        
        Args:
            issue: The detected issue
            namespace: Kubernetes namespace
            
        Returns:
            Dictionary with processing results
        """
        result = {
            "issue": issue.to_dict(),
            "diagnosed": False,
            "remediation_attempted": False,
            "approved": False
        }
        
        try:
            # Get additional context for diagnosis
            context = self._gather_context(issue, namespace)
            
            # Diagnose the issue
            diagnosis = self.diagnostician.diagnose(issue, context)
            result["diagnosis"] = diagnosis
            result["diagnosed"] = True
            
            logger.info(f"Diagnosis: {diagnosis.get('root_cause', 'Unknown')}")
            
            # Create remediation plan
            plan = self.remediator.create_remediation_plan(issue, diagnosis)
            result["remediation_plan"] = plan.to_dict()
            
            # Check if remediation should proceed
            if self._should_remediate(plan):
                result["approved"] = True
                result["remediation_attempted"] = True
                
                # Execute remediation
                remediation_result = self.remediator.execute_plan(plan)
                result["remediation_result"] = remediation_result
                
                # Store in history
                self.remediation_history.append({
                    "timestamp": time.time(),
                    "issue": issue.to_dict(),
                    "plan": plan.to_dict(),
                    "result": remediation_result
                })
            else:
                result["remediation_result"] = {
                    "success": False,
                    "message": "Remediation not approved or requires manual intervention"
                }
        
        except Exception as e:
            logger.error(f"Error processing issue: {e}")
            result["error"] = str(e)
        
        return result
    
    def _gather_context(self, issue: Issue, namespace: str) -> Dict[str, Any]:
        """
        Gather additional context for diagnosis
        
        Args:
            issue: The detected issue
            namespace: Kubernetes namespace
            
        Returns:
            Context dictionary
        """
        context = {}
        
        try:
            # Get pod logs if applicable
            if issue.resource_type == "Pod":
                logs = self.k8s_client.get_pod_logs(
                    issue.resource_name,
                    namespace,
                    tail_lines=50
                )
                context["logs"] = logs
            
            # Get recent events
            events = self.k8s_client.get_events(
                namespace,
                field_selector=f"involvedObject.name={issue.resource_name}"
            )
            context["events"] = events[:5]  # Last 5 events
            
        except Exception as e:
            logger.warning(f"Failed to gather context: {e}")
        
        return context
    
    def _should_remediate(self, plan: RemediationPlan) -> bool:
        """
        Determine if remediation should proceed based on safety checks
        
        Args:
            plan: The remediation plan
            
        Returns:
            True if remediation should proceed
        """
        # Check if manual intervention is required
        if plan.action.value == "manual_intervention":
            logger.info("Manual intervention required - skipping remediation")
            return False
        
        # Check if no action is needed
        if plan.action.value == "no_action":
            return True
        
        # Check risk level
        if plan.risk_level in ["high", "unknown"]:
            logger.warning(f"High risk remediation - requires approval: {plan.risk_level}")
            if self.config.require_approval:
                return False
        
        # Check remediation history to avoid loops
        recent_attempts = [
            h for h in self.remediation_history
            if h["issue"]["resource_name"] == plan.issue.resource_name
            and time.time() - h["timestamp"] < 3600  # Within last hour
        ]
        
        if len(recent_attempts) >= self.config.max_remediation_attempts:
            logger.warning(
                f"Max remediation attempts reached for {plan.issue.resource_name}"
            )
            return False
        
        return True
    
    def run_continuous(self, namespace: str = "default", 
                       interval: Optional[int] = None):
        """
        Run continuous monitoring and remediation
        
        Args:
            namespace: Kubernetes namespace to monitor
            interval: Check interval in seconds (uses config if not provided)
        """
        interval = interval or self.config.check_interval_seconds
        
        logger.info(
            f"Starting continuous monitoring of namespace '{namespace}' "
            f"with {interval}s interval"
        )
        
        try:
            while True:
                summary = self.run_once(namespace)
                
                # Log summary
                logger.info(
                    f"Cycle summary: {summary['issues_detected']} issues, "
                    f"{summary['remediations_successful']}/{summary['remediations_attempted']} "
                    f"successful remediations"
                )
                
                # Wait for next cycle
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Continuous monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error in continuous monitoring: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get agent status and statistics
        
        Returns:
            Status dictionary
        """
        return {
            "config": {
                "dry_run": self.config.dry_run,
                "require_approval": self.config.require_approval,
                "max_remediation_attempts": self.config.max_remediation_attempts
            },
            "remediation_history_count": len(self.remediation_history),
            "recent_remediations": self.remediation_history[-5:] if self.remediation_history else []
        }
