"""Pytest configuration and fixtures."""

import os
import sys
import pytest
from pathlib import Path

# Add src/ to Python path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def test_config():
    """Test configuration."""
    return {
        "llm": {
            "provider": "openrouter",
            "model": "meta-llama/llama-3.1-8b-instruct:free",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": os.getenv("OPENROUTER_API_KEY", "test-key"),
"""Pytest configuration."""

import pytest


@pytest.fixture
def mock_config():
    """Mock configuration for tests."""
    return {
        "llm": {
            "provider": "openrouter",
            "model": "openai/gpt-4o-mini",
            "base_url": "https://openrouter.ai/api/v1",
            "temperature": 0.1,
        },
        "qdrant": {
            "host": "localhost",
            "port": 6333,
            "collection": "test_failure_patterns",
            "collection": "test_patterns",
            "embedding_dim": 384,
        },
        "safety": {
            "dry_run_first": True,
            "require_approval": True,
        },
    }


@pytest.fixture
def mock_k8s_client():
    """Mock Kubernetes client."""
    from unittest.mock import Mock
    client = Mock()
    client.get_resource_state.return_value = {
        "namespace": "default",
        "resource_type": "Deployment",
        "resource_name": "test-app",
        "spec": {"replicas": 1},
    }
    client.has_oom_killed.return_value = True
    client.has_endpoints.return_value = False
    return client


@pytest.fixture
def scenarios_dir():
    """Path to scenarios directory."""
    return Path(__file__).parent / "scenarios"

        "cache": {
            "directory": ".cache/test",
            "diagnosis_ttl": 60,
        },
    }

