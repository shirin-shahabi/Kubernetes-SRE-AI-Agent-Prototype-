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
            "collection": "test_patterns",
            "embedding_dim": 384,
        },
        "safety": {
            "dry_run_first": True,
            "require_approval": True,
        },
        "cache": {
            "directory": ".cache/test",
            "diagnosis_ttl": 60,
        },
    }

