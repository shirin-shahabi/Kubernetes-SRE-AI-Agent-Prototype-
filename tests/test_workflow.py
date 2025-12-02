"""Test the complete SRE workflow."""

import pytest
from unittest.mock import Mock, patch

from sre_agent.agent import AgentState, SREAgent


class TestWorkflow:
    """Test complete workflow."""
    
    @patch('sre_agent.agent.QdrantClient')
    @patch('sre_agent.agent.K8sClient')
    @patch('sre_agent.agent.CacheManager')
    @patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test-key'})
    def test_detect_oom_workflow(self, mock_cache, mock_k8s_class, mock_qdrant):
        """Test OOM detection workflow."""
        # Mock K8s client
        mock_k8s = Mock()
        mock_k8s.get_resource_state.return_value = {
            "namespace": "default",
            "resource_type": "Deployment",
            "resource_name": "oom-app",
            "spec": {"containers": [{"resources": {"limits": {"memory": "64Mi"}}}]},
        }
        mock_k8s.has_oom_killed.return_value = True
        mock_k8s_class.return_value = mock_k8s
        
        agent = SREAgent()
        agent.k8s = mock_k8s
        
        # Test detect node
        state = AgentState({
            "namespace": "default",
            "resource_type": "Deployment",
            "resource_name": "oom-app",
        })
        
        result = agent._detect_node(state)
        
        assert result["detected"] is True
        assert result["failure_type"] == "OOMKilled"
    
    @patch('sre_agent.agent.QdrantClient')
    @patch('sre_agent.agent.K8sClient')
    @patch('sre_agent.agent.CacheManager')
    @patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test-key'})
    def test_detect_service_mismatch_workflow(self, mock_cache, mock_k8s_class, mock_qdrant):
        """Test Service mismatch detection workflow."""
        # Mock K8s client
        mock_k8s = Mock()
        mock_k8s.get_resource_state.return_value = {
            "namespace": "default",
            "resource_type": "Service",
            "resource_name": "broken-svc",
            "endpoints": {"subsets": []},
        }
        mock_k8s.has_endpoints.return_value = False
        mock_k8s_class.return_value = mock_k8s
        
        agent = SREAgent()
        agent.k8s = mock_k8s
        
        state = AgentState({
            "namespace": "default",
            "resource_type": "Service",
            "resource_name": "broken-svc",
        })
        
        result = agent._detect_node(state)
        
        assert result["detected"] is True
        assert result["failure_type"] == "ServiceMisconfigured"

