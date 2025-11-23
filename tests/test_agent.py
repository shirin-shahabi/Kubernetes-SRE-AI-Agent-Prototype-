"""
Basic tests to validate the SRE Agent structure
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sre_agent.detector import Issue, FailureType, FailureDetector
from sre_agent.remediator import RemediationAction, RemediationPlan


class TestIssue(unittest.TestCase):
    """Test Issue class"""
    
    def test_issue_creation(self):
        """Test creating an issue"""
        issue = Issue(
            failure_type=FailureType.POD_CRASH_LOOP,
            resource_type="Pod",
            resource_name="test-pod",
            namespace="default",
            details={"restart_count": 10}
        )
        
        self.assertEqual(issue.failure_type, FailureType.POD_CRASH_LOOP)
        self.assertEqual(issue.resource_name, "test-pod")
        self.assertEqual(issue.severity, "medium")
    
    def test_issue_to_dict(self):
        """Test issue serialization"""
        issue = Issue(
            failure_type=FailureType.POD_OOM_KILLED,
            resource_type="Pod",
            resource_name="oom-pod",
            namespace="default",
            details={"exit_code": 137}
        )
        
        issue_dict = issue.to_dict()
        self.assertEqual(issue_dict["failure_type"], "pod_oom_killed")
        self.assertEqual(issue_dict["severity"], "high")


class TestFailureDetector(unittest.TestCase):
    """Test FailureDetector class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_k8s_client = Mock()
    
    def test_detect_crash_loop(self):
        """Test crash loop detection"""
        # Mock pod with high restart count
        self.mock_k8s_client.get_all_pods.return_value = [{
            "name": "crasher",
            "namespace": "default",
            "status": "Running",
            "restart_count": 10,
            "conditions": [],
            "container_statuses": [{
                "name": "container",
                "ready": False,
                "restart_count": 10,
                "state": {
                    "waiting": {
                        "reason": "CrashLoopBackOff",
                        "message": "Back-off restarting"
                    }
                }
            }]
        }]
        
        self.mock_k8s_client.get_deployments.return_value = []
        
        detector = FailureDetector(self.mock_k8s_client)
        issues = detector.detect_issues("default")
        
        # Should detect both high restart count and crash loop
        self.assertGreater(len(issues), 0)
        issue_types = [i.failure_type for i in issues]
        self.assertIn(FailureType.POD_CRASH_LOOP, issue_types)
    
    def test_detect_image_pull_error(self):
        """Test image pull error detection"""
        self.mock_k8s_client.get_all_pods.return_value = [{
            "name": "imagepuller",
            "namespace": "default",
            "status": "Pending",
            "restart_count": 0,
            "conditions": [],
            "container_statuses": [{
                "name": "container",
                "ready": False,
                "restart_count": 0,
                "state": {
                    "waiting": {
                        "reason": "ImagePullBackOff",
                        "message": "Back-off pulling image"
                    }
                }
            }]
        }]
        
        self.mock_k8s_client.get_deployments.return_value = []
        
        detector = FailureDetector(self.mock_k8s_client)
        issues = detector.detect_issues("default")
        
        self.assertGreater(len(issues), 0)
        self.assertEqual(issues[0].failure_type, FailureType.POD_IMAGE_PULL_ERROR)
    
    def test_no_issues(self):
        """Test when no issues are present"""
        self.mock_k8s_client.get_all_pods.return_value = [{
            "name": "healthy-pod",
            "namespace": "default",
            "status": "Running",
            "restart_count": 0,
            "conditions": [],
            "container_statuses": [{
                "name": "container",
                "ready": True,
                "restart_count": 0,
                "state": {"running": True}
            }]
        }]
        
        self.mock_k8s_client.get_deployments.return_value = [{
            "name": "healthy-deploy",
            "namespace": "default",
            "replicas": 3,
            "ready_replicas": 3,
            "available_replicas": 3,
            "unavailable_replicas": 0
        }]
        
        detector = FailureDetector(self.mock_k8s_client)
        issues = detector.detect_issues("default")
        
        self.assertEqual(len(issues), 0)


class TestRemediationPlan(unittest.TestCase):
    """Test RemediationPlan class"""
    
    def test_plan_creation(self):
        """Test creating a remediation plan"""
        issue = Issue(
            failure_type=FailureType.POD_CRASH_LOOP,
            resource_type="Pod",
            resource_name="test-pod",
            namespace="default",
            details={}
        )
        
        plan = RemediationPlan(
            issue=issue,
            action=RemediationAction.DELETE_POD,
            parameters={"pod_name": "test-pod", "namespace": "default"},
            justification="Pod is crashing",
            risk_level="low"
        )
        
        self.assertEqual(plan.action, RemediationAction.DELETE_POD)
        self.assertEqual(plan.risk_level, "low")
    
    def test_plan_to_dict(self):
        """Test plan serialization"""
        issue = Issue(
            failure_type=FailureType.DEPLOYMENT_UNAVAILABLE,
            resource_type="Deployment",
            resource_name="test-deploy",
            namespace="default",
            details={}
        )
        
        plan = RemediationPlan(
            issue=issue,
            action=RemediationAction.RESTART_DEPLOYMENT,
            parameters={"deployment_name": "test-deploy"},
            justification="Deployment unavailable",
            risk_level="medium"
        )
        
        plan_dict = plan.to_dict()
        self.assertEqual(plan_dict["action"], "restart_deployment")
        self.assertEqual(plan_dict["risk_level"], "medium")


if __name__ == '__main__':
    unittest.main()
