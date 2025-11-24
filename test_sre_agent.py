"""
Unit tests for the Kubernetes SRE Agent.

These tests verify the core functionality of the SRE agent using mocked Kubernetes API calls.
"""

import pytest
from unittest.mock import Mock, patch
from kubernetes.client.rest import ApiException
from sre_agent import KubernetesSREAgent


@pytest.fixture
def mock_k8s_config():
    """Mock Kubernetes configuration loading."""
    with patch("sre_agent.config.load_kube_config") as mock_config:
        yield mock_config


@pytest.fixture
def mock_core_v1_api():
    """Mock Kubernetes CoreV1Api."""
    with patch("sre_agent.client.CoreV1Api") as mock_api:
        yield mock_api.return_value


@pytest.fixture
def mock_apps_v1_api():
    """Mock Kubernetes AppsV1Api."""
    with patch("sre_agent.client.AppsV1Api") as mock_api:
        yield mock_api.return_value


@pytest.fixture
def agent(mock_k8s_config, mock_core_v1_api, mock_apps_v1_api):
    """Create a SRE agent instance with mocked Kubernetes clients."""
    return KubernetesSREAgent()


class TestKubernetesSREAgent:
    """Test suite for KubernetesSREAgent class."""

    def test_initialization_success(self, mock_k8s_config):
        """Test successful agent initialization."""
        agent = KubernetesSREAgent()
        assert agent is not None
        assert mock_k8s_config.called

    def test_initialization_with_custom_kubeconfig(self):
        """Test agent initialization with custom kubeconfig path."""
        with patch("sre_agent.config.load_kube_config") as mock_config:
            _ = KubernetesSREAgent(kubeconfig_path="/custom/kubeconfig")
            mock_config.assert_called_once_with(config_file="/custom/kubeconfig")

    def test_detect_pod_failures_with_failed_pods(self, agent, mock_core_v1_api):
        """Test detection of failed pods."""
        # Mock pod list with failed pod
        mock_pod = Mock()
        mock_pod.metadata.name = "failed-pod"
        mock_pod.status.phase = "Failed"
        mock_pod.status.reason = "Error"
        mock_pod.status.message = "Container exited with error"
        mock_pod.status.container_statuses = None

        mock_pod_list = Mock()
        mock_pod_list.items = [mock_pod]

        mock_core_v1_api.list_namespaced_pod.return_value = mock_pod_list

        failed_pods = agent.detect_pod_failures(namespace="default")

        assert len(failed_pods) == 1
        assert failed_pods[0]["name"] == "failed-pod"
        assert failed_pods[0]["status"] == "Failed"
        assert failed_pods[0]["reason"] == "Error"

    def test_detect_pod_failures_with_crashloop(self, agent, mock_core_v1_api):
        """Test detection of pods in CrashLoopBackOff state."""
        # Mock pod with CrashLoopBackOff
        mock_pod = Mock()
        mock_pod.metadata.name = "crashloop-pod"
        mock_pod.status.phase = "Running"

        # Mock container status
        mock_container_status = Mock()
        mock_container_status.name = "app-container"
        mock_container_status.state.waiting.reason = "CrashLoopBackOff"
        mock_container_status.state.waiting.message = "Back-off restarting failed container"

        mock_pod.status.container_statuses = [mock_container_status]

        mock_pod_list = Mock()
        mock_pod_list.items = [mock_pod]

        mock_core_v1_api.list_namespaced_pod.return_value = mock_pod_list

        failed_pods = agent.detect_pod_failures(namespace="default")

        assert len(failed_pods) == 1
        assert failed_pods[0]["name"] == "crashloop-pod"
        assert failed_pods[0]["status"] == "CrashLoopBackOff"
        assert failed_pods[0]["container"] == "app-container"

    def test_detect_pod_failures_with_healthy_pods(self, agent, mock_core_v1_api):
        """Test that healthy pods are not reported as failed."""
        # Mock healthy pod
        mock_pod = Mock()
        mock_pod.metadata.name = "healthy-pod"
        mock_pod.status.phase = "Running"
        mock_pod.status.container_statuses = None

        mock_pod_list = Mock()
        mock_pod_list.items = [mock_pod]

        mock_core_v1_api.list_namespaced_pod.return_value = mock_pod_list

        failed_pods = agent.detect_pod_failures(namespace="default")

        assert len(failed_pods) == 0

    def test_detect_pod_failures_api_exception(self, agent, mock_core_v1_api):
        """Test handling of API exceptions during pod failure detection."""
        mock_core_v1_api.list_namespaced_pod.side_effect = ApiException("API Error")

        with pytest.raises(ApiException):
            agent.detect_pod_failures(namespace="default")

    def test_restart_failed_pod_success(self, agent, mock_core_v1_api):
        """Test successful pod restart."""
        mock_core_v1_api.delete_namespaced_pod.return_value = Mock()

        result = agent.restart_failed_pod("failed-pod", namespace="default")

        assert result is True
        mock_core_v1_api.delete_namespaced_pod.assert_called_once()

    def test_restart_failed_pod_api_exception(self, agent, mock_core_v1_api):
        """Test handling of API exceptions during pod restart."""
        mock_core_v1_api.delete_namespaced_pod.side_effect = ApiException("Delete failed")

        result = agent.restart_failed_pod("failed-pod", namespace="default")

        assert result is False

    def test_get_pod_logs_success(self, agent, mock_core_v1_api):
        """Test successful retrieval of pod logs."""
        expected_logs = "Application started\nError: Connection failed\n"
        mock_core_v1_api.read_namespaced_pod_log.return_value = expected_logs

        logs = agent.get_pod_logs("test-pod", namespace="default", tail_lines=100)

        assert logs == expected_logs
        mock_core_v1_api.read_namespaced_pod_log.assert_called_once_with(
            name="test-pod", namespace="default", tail_lines=100
        )

    def test_get_pod_logs_api_exception(self, agent, mock_core_v1_api):
        """Test handling of API exceptions during log retrieval."""
        mock_core_v1_api.read_namespaced_pod_log.side_effect = ApiException("Log retrieval failed")

        logs = agent.get_pod_logs("test-pod", namespace="default")

        assert logs == ""

    def test_check_deployment_health_healthy(self, agent, mock_apps_v1_api):
        """Test checking health of a healthy deployment."""
        mock_deployment = Mock()
        mock_deployment.metadata.name = "test-deployment"
        mock_deployment.spec.replicas = 3
        mock_deployment.status.ready_replicas = 3
        mock_deployment.status.available_replicas = 3

        mock_apps_v1_api.read_namespaced_deployment.return_value = mock_deployment

        health = agent.check_deployment_health("test-deployment", namespace="default")

        assert health["name"] == "test-deployment"
        assert health["desired_replicas"] == 3
        assert health["ready_replicas"] == 3
        assert health["is_healthy"] is True

    def test_check_deployment_health_unhealthy(self, agent, mock_apps_v1_api):
        """Test checking health of an unhealthy deployment."""
        mock_deployment = Mock()
        mock_deployment.metadata.name = "test-deployment"
        mock_deployment.spec.replicas = 3
        mock_deployment.status.ready_replicas = 1
        mock_deployment.status.available_replicas = 1

        mock_apps_v1_api.read_namespaced_deployment.return_value = mock_deployment

        health = agent.check_deployment_health("test-deployment", namespace="default")

        assert health["is_healthy"] is False
        assert health["ready_replicas"] == 1

    def test_check_deployment_health_api_exception(self, agent, mock_apps_v1_api):
        """Test handling of API exceptions during deployment health check."""
        mock_apps_v1_api.read_namespaced_deployment.side_effect = ApiException("Deployment not found")

        with pytest.raises(ApiException):
            agent.check_deployment_health("test-deployment", namespace="default")

    def test_scale_deployment_success(self, agent, mock_apps_v1_api):
        """Test successful deployment scaling."""
        mock_apps_v1_api.patch_namespaced_deployment_scale.return_value = Mock()

        result = agent.scale_deployment("test-deployment", replicas=5, namespace="default")

        assert result is True
        mock_apps_v1_api.patch_namespaced_deployment_scale.assert_called_once()

    def test_scale_deployment_api_exception(self, agent, mock_apps_v1_api):
        """Test handling of API exceptions during deployment scaling."""
        mock_apps_v1_api.patch_namespaced_deployment_scale.side_effect = ApiException("Scaling failed")

        result = agent.scale_deployment("test-deployment", replicas=5, namespace="default")

        assert result is False


class TestLogging:
    """Test suite for logging configuration."""

    def test_setup_logging_default_level(self):
        """Test logging setup with default INFO level."""
        from sre_agent import setup_logging

        setup_logging()

        import logging

        logger = logging.getLogger("sre_agent")
        assert logger.level <= logging.INFO

    def test_setup_logging_custom_level(self):
        """Test logging setup with custom DEBUG level."""
        from sre_agent import setup_logging

        setup_logging(level="DEBUG")

        import logging

        logger = logging.getLogger("sre_agent")
        assert logger.level <= logging.DEBUG
