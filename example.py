#!/usr/bin/env python
"""
Example usage of the Kubernetes SRE Agent.

This script demonstrates how to use the SRE agent to monitor and remediate
Kubernetes cluster failures.
"""

import time
from sre_agent import KubernetesSREAgent, setup_logging


def main():
    """Main function to demonstrate SRE agent capabilities."""
    # Setup logging
    setup_logging(level="INFO")

    print("=" * 80)
    print("Kubernetes SRE AI Agent - Example Usage")
    print("=" * 80)
    print()

    # Initialize the agent
    try:
        print("Initializing SRE agent...")
        agent = KubernetesSREAgent()
        print("✓ SRE agent initialized successfully")
        print()
    except Exception as e:
        print(f"✗ Failed to initialize agent: {e}")
        print("\nPlease ensure:")
        print("  1. You have kubectl configured with cluster access")
        print("  2. Your kubeconfig file is properly set up")
        print("  3. You have permissions to access the cluster")
        return

    # Example 1: Detect failed pods
    print("-" * 80)
    print("Example 1: Detecting Failed Pods")
    print("-" * 80)
    try:
        failed_pods = agent.detect_pod_failures(namespace="default")
        if failed_pods:
            print(f"Found {len(failed_pods)} failed pod(s):")
            for pod in failed_pods:
                print(f"  - {pod['name']}: {pod['status']}")
        else:
            print("✓ No failed pods detected in 'default' namespace")
    except Exception as e:
        print(f"✗ Error detecting pod failures: {e}")
    print()

    # Example 2: Check deployment health
    print("-" * 80)
    print("Example 2: Checking Deployment Health")
    print("-" * 80)
    print("Note: Replace 'my-deployment' with an actual deployment name in your cluster")
    # Uncomment and modify the deployment name to test:
    # try:
    #     health = agent.check_deployment_health("my-deployment", namespace="default")
    #     print(f"Deployment: {health['name']}")
    #     print(f"  Desired replicas: {health['desired_replicas']}")
    #     print(f"  Ready replicas: {health['ready_replicas']}")
    #     print(f"  Health status: {'✓ Healthy' if health['is_healthy'] else '✗ Unhealthy'}")
    # except Exception as e:
    #     print(f"✗ Error checking deployment: {e}")
    print("(Commented out - uncomment and modify deployment name to test)")
    print()

    # Example 3: Automated remediation
    print("-" * 80)
    print("Example 3: Automated Remediation")
    print("-" * 80)
    print("Monitoring for failed pods and automatically remediating...")
    print("(Monitoring for 30 seconds - Press Ctrl+C to stop)")
    print()

    try:
        for i in range(6):  # Monitor for 30 seconds (6 iterations x 5 seconds)
            failed_pods = agent.detect_pod_failures(namespace="default")
            if failed_pods:
                print(f"[{time.strftime('%H:%M:%S')}] Found {len(failed_pods)} failed pod(s)")
                for pod in failed_pods:
                    pod_name = pod["name"]
                    print(f"  Attempting to remediate: {pod_name}")
                    # In production, you might want to add additional checks here
                    # before automatically restarting pods
                    success = agent.restart_failed_pod(pod_name, namespace="default")
                    if success:
                        print(f"  ✓ Successfully initiated restart for {pod_name}")
                    else:
                        print(f"  ✗ Failed to restart {pod_name}")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] ✓ All pods healthy")

            if i < 5:  # Don't sleep on the last iteration
                time.sleep(5)
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
    except Exception as e:
        print(f"\n✗ Error during monitoring: {e}")

    print()
    print("=" * 80)
    print("Example completed")
    print("=" * 80)


if __name__ == "__main__":
    main()
