"""Unit tests for SRE Agent."""

import pytest
from unittest.mock import Mock, patch

from sre_agent.agent import AgentState, SREAgent
from sre_agent.k8s_client import K8sClient


class TestAgent:
    """Test SRE Agent."""
    
    @patch('sre_agent.agent.QdrantClient')
    @patch('sre_agent.agent.K8sClient')
    @patch('sre_agent.agent.CacheManager')
    def test_agent_initialization(self, mock_cache, mock_k8s, mock_qdrant):
        """Test agent initialization."""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test-key'}):
            agent = SREAgent()
            assert agent is not None
            assert agent.k8s is not None
            assert agent.cache is not None
    
    def test_agent_state(self):
        """Test AgentState."""
        state = AgentState({
            "namespace": "default",
            "resource_type": "Deployment",
            "resource_name": "test-app",
        })
        assert state["namespace"] == "default"
        assert state["resource_type"] == "Deployment"


class TestK8sClient:
    """Test Kubernetes client."""
    
    @patch('sre_agent.k8s_client.config')
    def test_k8s_client_init(self, mock_config):
        """Test K8s client initialization."""
        client = K8sClient()
        assert client.core_v1 is not None
        assert client.apps_v1 is not None
    
    def test_has_oom_killed(self):
        """Test OOM detection."""
        client = K8sClient()
        # Mock pod with OOMKilled
        with patch.object(client.core_v1, 'list_namespaced_pod') as mock_list:
            mock_pod = Mock()
            mock_pod.status.container_statuses = [Mock()]
            mock_pod.status.container_statuses[0].last_state = Mock()
            mock_pod.status.container_statuses[0].last_state.terminated = Mock()
            mock_pod.status.container_statuses[0].last_state.terminated.reason = "OOMKilled"
            mock_list.return_value.items = [mock_pod]
            
            result = client.has_oom_killed("default", "test-app")
            assert result is True

