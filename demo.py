#!/usr/bin/env python3
"""
Demo script showing the SRE Agent capabilities without requiring
a Kubernetes cluster or OpenAI API key.

This demonstrates the detection and remediation logic using mock data.
"""
import sys
import os
from unittest.mock import Mock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sre_agent.detector import FailureDetector, Issue, FailureType
from sre_agent.remediator import Remediator, RemediationAction


def print_section(title):
    """Print a section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def demo_detection():
    """Demonstrate issue detection"""
    print_section("DETECTION DEMO")
    
    # Create mock Kubernetes client
    mock_k8s = Mock()
    
    # Mock data: various problematic pods
    mock_k8s.get_all_pods.return_value = [
        {
            "name": "crashloop-pod",
            "namespace": "default",
            "status": "Running",
            "restart_count": 15,
            "conditions": [],
            "container_statuses": [{
                "name": "app",
                "ready": False,
                "restart_count": 15,
                "state": {
                    "waiting": {
                        "reason": "CrashLoopBackOff",
                        "message": "Back-off 5m0s restarting failed container"
                    }
                }
            }]
        },
        {
            "name": "imagepull-pod",
            "namespace": "default",
            "status": "Pending",
            "restart_count": 0,
            "conditions": [],
            "container_statuses": [{
                "name": "app",
                "ready": False,
                "restart_count": 0,
                "state": {
                    "waiting": {
                        "reason": "ImagePullBackOff",
                        "message": "Failed to pull image 'nonexistent:latest'"
                    }
                }
            }]
        },
        {
            "name": "oom-pod",
            "namespace": "default",
            "status": "Running",
            "restart_count": 3,
            "conditions": [],
            "container_statuses": [{
                "name": "app",
                "ready": False,
                "restart_count": 3,
                "state": {
                    "terminated": {
                        "reason": "OOMKilled",
                        "exit_code": 137,
                        "message": "Container killed due to memory limit"
                    }
                }
            }]
        },
        {
            "name": "healthy-pod",
            "namespace": "default",
            "status": "Running",
            "restart_count": 0,
            "conditions": [],
            "container_statuses": [{
                "name": "app",
                "ready": True,
                "restart_count": 0,
                "state": {"running": True}
            }]
        }
    ]
    
    # Mock deployment data
    mock_k8s.get_deployments.return_value = [
        {
            "name": "unavailable-deployment",
            "namespace": "default",
            "replicas": 3,
            "ready_replicas": 1,
            "available_replicas": 1,
            "unavailable_replicas": 2
        },
        {
            "name": "healthy-deployment",
            "namespace": "default",
            "replicas": 3,
            "ready_replicas": 3,
            "available_replicas": 3,
            "unavailable_replicas": 0
        }
    ]
    
    # Create detector and detect issues
    detector = FailureDetector(mock_k8s)
    issues = detector.detect_issues("default")
    
    print(f"\n✓ Scanned namespace 'default'")
    print(f"✓ Found {len(issues)} issues\n")
    
    # Display detected issues
    for i, issue in enumerate(issues, 1):
        print(f"{i}. {issue}")
        print(f"   Details: {issue.details}")
    
    return issues


def demo_diagnosis(issues):
    """Demonstrate diagnosis (mocked since we don't have API key)"""
    print_section("DIAGNOSIS DEMO")
    
    # Mock diagnoses for each issue type
    mock_diagnoses = {
        FailureType.POD_CRASH_LOOP: {
            "root_cause": "Container exits immediately after starting",
            "explanation": "The container's main process is failing to start properly. "
                         "This could be due to missing dependencies, incorrect configuration, "
                         "or application bugs.",
            "recommendations": [
                "Check application logs for startup errors",
                "Verify environment variables and configuration",
                "Ensure all dependencies are available"
            ],
            "confidence": "high"
        },
        FailureType.POD_IMAGE_PULL_ERROR: {
            "root_cause": "Container image cannot be pulled from registry",
            "explanation": "The specified container image does not exist or is not accessible. "
                         "This could be due to incorrect image name/tag, registry authentication "
                         "issues, or network problems.",
            "recommendations": [
                "Verify the image name and tag are correct",
                "Check registry credentials and pull secrets",
                "Ensure registry is accessible from the cluster"
            ],
            "confidence": "high"
        },
        FailureType.POD_OOM_KILLED: {
            "root_cause": "Container exceeded memory limits",
            "explanation": "The container used more memory than allocated, causing Kubernetes "
                         "to terminate it. This indicates either memory limits are too low or "
                         "the application has a memory leak.",
            "recommendations": [
                "Increase memory limits in pod specification",
                "Investigate application for memory leaks",
                "Review resource usage patterns and optimize"
            ],
            "confidence": "high"
        },
        FailureType.DEPLOYMENT_UNAVAILABLE: {
            "root_cause": "Deployment pods are failing to become ready",
            "explanation": "The deployment cannot maintain the desired number of healthy replicas. "
                         "This could be due to pod failures, resource constraints, or configuration issues.",
            "recommendations": [
                "Check pod status and events for underlying issues",
                "Verify resource availability in the cluster",
                "Review deployment configuration and health checks"
            ],
            "confidence": "medium"
        },
        FailureType.HIGH_RESTART_COUNT: {
            "root_cause": "Pod is repeatedly restarting",
            "explanation": "The pod has accumulated many restarts, indicating persistent issues "
                         "with the container. This suggests recurring failures that need investigation.",
            "recommendations": [
                "Analyze pod logs across multiple restarts",
                "Check for resource constraints or configuration errors",
                "Review liveness and readiness probes"
            ],
            "confidence": "high"
        }
    }
    
    print("\n✓ Using AI to diagnose each issue...\n")
    
    diagnoses = []
    for i, issue in enumerate(issues, 1):
        diagnosis = mock_diagnoses.get(issue.failure_type, {
            "root_cause": "Unknown issue",
            "explanation": "Further investigation required",
            "recommendations": ["Manual investigation needed"],
            "confidence": "low"
        })
        
        print(f"{i}. Diagnosis for {issue.resource_name}:")
        print(f"   Root Cause: {diagnosis['root_cause']}")
        print(f"   Confidence: {diagnosis['confidence']}")
        print(f"   Recommendations:")
        for rec in diagnosis['recommendations']:
            print(f"     • {rec}")
        print()
        
        diagnoses.append(diagnosis)
    
    return diagnoses


def demo_remediation(issues, diagnoses):
    """Demonstrate remediation planning"""
    print_section("REMEDIATION DEMO")
    
    # Create mock Kubernetes client
    mock_k8s = Mock()
    mock_k8s.delete_pod.return_value = True
    mock_k8s.restart_deployment.return_value = True
    
    # Create remediator in dry-run mode
    remediator = Remediator(mock_k8s, dry_run=True)
    
    print("\n✓ Creating remediation plans (DRY RUN mode)...\n")
    
    for i, (issue, diagnosis) in enumerate(zip(issues, diagnoses), 1):
        plan = remediator.create_remediation_plan(issue, diagnosis)
        
        print(f"{i}. Remediation Plan for {issue.resource_name}:")
        print(f"   Action: {plan.action.value}")
        print(f"   Risk Level: {plan.risk_level}")
        print(f"   Justification: {plan.justification}")
        
        # Simulate execution
        result = remediator.execute_plan(plan)
        status = "✓ SUCCESS" if result['success'] else "✗ FAILED"
        print(f"   Execution: {status} - {result['message']}")
        print()


def main():
    """Run the demo"""
    print("\n" + "="*70)
    print("  KUBERNETES SRE AI AGENT - DEMO")
    print("  (Running with mock data - no cluster or API key required)")
    print("="*70)
    
    # Step 1: Detection
    issues = demo_detection()
    
    if not issues:
        print("\n✓ No issues detected! Cluster is healthy.")
        return
    
    # Step 2: Diagnosis
    diagnoses = demo_diagnosis(issues)
    
    # Step 3: Remediation
    demo_remediation(issues, diagnoses)
    
    # Summary
    print_section("SUMMARY")
    print(f"\n✓ Detected {len(issues)} issues")
    print(f"✓ Diagnosed all issues using AI reasoning")
    print(f"✓ Created remediation plans with safety checks")
    print(f"✓ Executed remediations (DRY RUN - no actual changes)")
    print("\nThis demo shows the complete pipeline:")
    print("  Detection → Diagnosis → Remediation")
    print("\nTo use with a real cluster, see QUICKSTART.md")
    print()


if __name__ == '__main__':
    main()
