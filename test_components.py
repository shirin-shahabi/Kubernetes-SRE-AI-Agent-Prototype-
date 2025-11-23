#!/usr/bin/env python3
"""
Simple test/demo script to validate the agent components work correctly.
This doesn't require a real Kubernetes cluster - it tests the logic.
"""
import sys
from src.diagnostics import Diagnostics


def test_oomkilled_diagnosis():
    """Test OOMKilled diagnosis logic."""
    print("Testing OOMKilled diagnosis logic...")
    
    # Mock pod status with OOMKilled container
    pod_status = {
        'name': 'test-pod',
        'namespace': 'default',
        'phase': 'Running',
        'container_statuses': [
            {
                'name': 'test-container',
                'ready': False,
                'restart_count': 5,
                'state': {'state': 'running'},
                'last_state': {
                    'state': 'terminated',
                    'reason': 'OOMKilled',
                    'exit_code': 137
                }
            }
        ]
    }
    
    # Mock deployment info
    deployment_info = {
        'name': 'test-deployment',
        'namespace': 'default',
        'containers': [
            {
                'name': 'test-container',
                'image': 'test:latest',
                'resources': {
                    'requests': {'memory': '50Mi'},
                    'limits': {'memory': '50Mi'}
                }
            }
        ]
    }
    
    # Run diagnosis
    diagnostics = Diagnostics()
    result = diagnostics.diagnose_oomkilled_pod(pod_status, deployment_info)
    
    # Validate results
    assert result['issue_detected'], "OOMKilled issue should be detected"
    assert result['issue_type'] == 'OOMKilled', "Issue type should be OOMKilled"
    assert 'memory' in result['root_cause'].lower(), "Root cause should mention memory"
    assert result['suggested_fix']['action'] == 'increase_memory_limit', "Should suggest memory increase"
    assert result['suggested_fix']['suggested_limit'] == '150Mi', "Should suggest 3x increase (50Mi -> 150Mi)"
    
    print("✅ OOMKilled diagnosis test passed!")
    print(f"   Root cause: {result['root_cause'][:100]}...")
    print(f"   Suggested fix: {result['suggested_fix']['current_limit']} -> {result['suggested_fix']['suggested_limit']}")


def test_service_diagnosis():
    """Test broken service diagnosis logic."""
    print("\nTesting broken service diagnosis logic...")
    
    # Mock service info with incorrect selector
    service_info = {
        'name': 'test-service',
        'namespace': 'default',
        'selector': {
            'app': 'test-app',
            'version': 'v2'  # Mismatch!
        }
    }
    
    # Mock endpoints (no endpoints)
    endpoints_info = {
        'name': 'test-service',
        'namespace': 'default',
        'subsets': []  # No endpoints
    }
    
    # Mock pods with different labels
    pods_info = [
        {
            'name': 'test-pod-1',
            'namespace': 'default',
            'phase': 'Running',
            'labels': {
                'app': 'test-app',
                'version': 'v1'  # Different from service selector
            }
        },
        {
            'name': 'test-pod-2',
            'namespace': 'default',
            'phase': 'Running',
            'labels': {
                'app': 'test-app',
                'version': 'v1'
            }
        }
    ]
    
    # Run diagnosis
    diagnostics = Diagnostics()
    result = diagnostics.diagnose_service_endpoints(service_info, endpoints_info, pods_info)
    
    # Validate results
    assert result['issue_detected'], "Service endpoint issue should be detected"
    assert result['issue_type'] == 'ServiceEndpointMismatch', "Issue type should be ServiceEndpointMismatch"
    assert 'label' in result['root_cause'].lower(), "Root cause should mention labels"
    assert result['suggested_fix']['action'] == 'fix_service_selector', "Should suggest fixing selector"
    assert result['suggested_fix']['suggested_selector']['version'] == 'v1', "Should suggest correct version label"
    
    print("✅ Broken service diagnosis test passed!")
    print(f"   Mismatched labels: {result['details']['mismatched_labels']}")
    print(f"   Suggested selector: {result['suggested_fix']['suggested_selector']}")


def test_memory_limit_calculation():
    """Test memory limit calculation."""
    print("\nTesting memory limit calculation...")
    
    diagnostics = Diagnostics()
    
    test_cases = [
        ("50Mi", "150Mi"),
        ("100Mi", "300Mi"),
        ("1Gi", "3Gi"),
        ("512Mi", "1536Mi"),
        ("Not set", "256Mi"),
    ]
    
    for current, expected in test_cases:
        result = diagnostics._calculate_new_memory_limit(current)
        assert result == expected, f"Expected {expected} for {current}, got {result}"
        print(f"   {current} -> {result} ✓")
    
    print("✅ Memory limit calculation test passed!")


def main():
    """Run all tests."""
    print("=" * 80)
    print("Running SRE AI Agent Component Tests")
    print("=" * 80)
    
    try:
        test_oomkilled_diagnosis()
        test_service_diagnosis()
        test_memory_limit_calculation()
        
        print("\n" + "=" * 80)
        print("✅ All tests passed!")
        print("=" * 80)
        print("\nThe agent components are working correctly.")
        print("To test with a real Kubernetes cluster, deploy the test scenarios:")
        print("  kubectl apply -f k8s-manifests/scenario-a-oom.yaml")
        print("  kubectl apply -f k8s-manifests/scenario-b-broken-service.yaml")
        print("\nThen run the CLI:")
        print("  python cli.py --scenario oomkilled --namespace default --deployment oom-app")
        print("  python cli.py --scenario broken-service --namespace default --service broken-service")
        
        return 0
    
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
