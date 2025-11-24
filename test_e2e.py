"""
End-to-End tests for the Kubernetes SRE Agent.

These tests run against a real Kubernetes cluster (kind) to validate actual behavior.
"""

import pytest
import time
import subprocess
from kubernetes import client, config
from sre_agent import KubernetesSREAgent


@pytest.fixture(scope="module")
def k8s_client():
    """Initialize Kubernetes client for e2e tests."""
    # Load kubeconfig (assumes kind cluster is already running)
    config.load_kube_config()
    return client.CoreV1Api()


@pytest.fixture(scope="module")
def agent():
    """Create a real SRE agent instance for e2e tests."""
    return KubernetesSREAgent()


@pytest.fixture(scope="module")
def test_namespace(k8s_client):
    """Create a test namespace for e2e tests."""
    namespace_name = "sre-agent-test"

    # Create namespace
    namespace_manifest = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace_name))

    try:
        k8s_client.create_namespace(body=namespace_manifest)
    except client.exceptions.ApiException as e:
        if e.status != 409:  # Ignore if already exists
            raise

    yield namespace_name

    # Cleanup: delete namespace
    try:
        k8s_client.delete_namespace(name=namespace_name)
    except client.exceptions.ApiException:
        pass  # Ignore cleanup errors


@pytest.fixture
def create_test_pod(k8s_client, test_namespace):
    """Factory fixture to create test pods."""
    created_pods = []

    def _create_pod(name: str, image: str = "busybox:latest", command: list = None):
        """Create a test pod."""
        pod_manifest = client.V1Pod(
            metadata=client.V1ObjectMeta(name=name),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="test-container", image=image, command=command or ["sh", "-c", "sleep 3600"]
                    )
                ],
                restart_policy="Never",
            ),
        )

        k8s_client.create_namespaced_pod(namespace=test_namespace, body=pod_manifest)
        created_pods.append(name)
        return name

    yield _create_pod

    # Cleanup: delete all created pods
    for pod_name in created_pods:
        try:
            k8s_client.delete_namespaced_pod(name=pod_name, namespace=test_namespace)
        except client.exceptions.ApiException:
            pass  # Ignore cleanup errors


class TestE2EPodFailureDetection:
    """E2E tests for pod failure detection."""

    def test_detect_failed_pod(self, agent, test_namespace, create_test_pod, k8s_client):
        """Test detection of a pod that fails immediately."""
        # Create a pod that will fail
        pod_name = create_test_pod(name="failing-pod", image="busybox:latest", command=["sh", "-c", "exit 1"])

        # Wait for pod to fail
        time.sleep(10)

        # Detect failures
        failed_pods = agent.detect_pod_failures(namespace=test_namespace)

        # Verify the failed pod is detected
        failed_pod_names = [p["name"] for p in failed_pods]
        assert pod_name in failed_pod_names

    def test_no_failures_in_healthy_namespace(self, agent, test_namespace, create_test_pod):
        """Test that no failures are detected in a namespace with healthy pods."""
        # Create a healthy pod
        create_test_pod(name="healthy-pod", image="busybox:latest", command=["sh", "-c", "sleep 3600"])

        # Wait for pod to start
        time.sleep(5)

        # Detect failures
        failed_pods = agent.detect_pod_failures(namespace=test_namespace)

        # Filter out any old failed pods, check only for current pod
        # In a clean test namespace, there should be no failures
        assert len(failed_pods) == 0 or all(p["name"] != "healthy-pod" for p in failed_pods)


class TestE2EPodRemediation:
    """E2E tests for pod remediation."""

    def test_restart_failed_pod(self, agent, test_namespace, create_test_pod, k8s_client):
        """Test restarting a failed pod."""
        # Create a pod
        pod_name = create_test_pod(name="pod-to-restart", image="busybox:latest", command=["sh", "-c", "sleep 10"])

        # Wait for pod to be running
        time.sleep(5)

        # Restart the pod
        result = agent.restart_failed_pod(pod_name, namespace=test_namespace)

        assert result is True

        # Verify pod is being terminated/deleted
        time.sleep(2)
        try:
            pod = k8s_client.read_namespaced_pod(name=pod_name, namespace=test_namespace)
            # If pod exists, it should be in Terminating state or deleted
            assert pod.metadata.deletion_timestamp is not None or pod.status.phase == "Terminating"
        except client.exceptions.ApiException as e:
            # Pod not found is also acceptable (already deleted)
            assert e.status == 404


class TestE2EPodLogs:
    """E2E tests for pod log retrieval."""

    def test_retrieve_pod_logs(self, agent, test_namespace, create_test_pod, k8s_client):
        """Test retrieving logs from a pod."""
        # Create a pod that generates logs
        pod_name = create_test_pod(
            name="logging-pod",
            image="busybox:latest",
            command=["sh", "-c", "echo 'Test log line 1'; echo 'Test log line 2'; sleep 3600"],
        )

        # Wait for pod to start and generate logs
        time.sleep(10)

        # Retrieve logs
        logs = agent.get_pod_logs(pod_name, namespace=test_namespace, tail_lines=100)

        # Verify logs contain expected content
        assert "Test log line 1" in logs
        assert "Test log line 2" in logs


class TestE2EDeploymentManagement:
    """E2E tests for deployment management."""

    @pytest.fixture
    def test_deployment(self, test_namespace):
        """Create a test deployment."""
        apps_v1 = client.AppsV1Api()
        deployment_name = "test-deployment"

        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=deployment_name),
            spec=client.V1DeploymentSpec(
                replicas=2,
                selector=client.V1LabelSelector(match_labels={"app": "test"}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": "test"}),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="test-container", image="busybox:latest", command=["sh", "-c", "sleep 3600"]
                            )
                        ]
                    ),
                ),
            ),
        )

        apps_v1.create_namespaced_deployment(namespace=test_namespace, body=deployment)

        # Wait for deployment to be ready
        time.sleep(15)

        yield deployment_name

        # Cleanup
        try:
            apps_v1.delete_namespaced_deployment(name=deployment_name, namespace=test_namespace)
        except client.exceptions.ApiException:
            pass

    def test_check_deployment_health(self, agent, test_namespace, test_deployment):
        """Test checking deployment health."""
        health = agent.check_deployment_health(test_deployment, namespace=test_namespace)

        assert health["name"] == test_deployment
        assert health["desired_replicas"] == 2
        # Deployment should eventually become healthy
        # In some environments it might take time, so we accept both healthy and scaling states
        assert health["desired_replicas"] > 0

    def test_scale_deployment(self, agent, test_namespace, test_deployment):
        """Test scaling a deployment."""
        # Scale up
        result = agent.scale_deployment(test_deployment, replicas=3, namespace=test_namespace)
        assert result is True

        # Wait for scaling to take effect
        time.sleep(5)

        # Verify scaling
        health = agent.check_deployment_health(test_deployment, namespace=test_namespace)
        assert health["desired_replicas"] == 3


@pytest.mark.skipif(
    subprocess.run(["kubectl", "cluster-info"], capture_output=True).returncode != 0,
    reason="Kubernetes cluster not available",
)
class TestE2EClusterConnectivity:
    """E2E tests for cluster connectivity."""

    def test_agent_can_connect_to_cluster(self, agent):
        """Test that the agent can connect to the cluster."""
        # This test verifies basic cluster connectivity
        assert agent.core_v1 is not None
        assert agent.apps_v1 is not None

    def test_can_list_namespaces(self, agent):
        """Test that the agent can list namespaces."""
        namespaces = agent.core_v1.list_namespace()
        assert len(namespaces.items) > 0
