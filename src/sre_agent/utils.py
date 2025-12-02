"""Utility functions."""

import os
import yaml
from pathlib import Path

import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
)


def get_logger(name: str = __name__):
    """Get structured logger."""
    return structlog.get_logger(name)


def load_config() -> dict:
    """Load configuration from YAML."""
    # Find config relative to project root
    current = Path(__file__)
    # Go up from src/sre_agent/utils.py to project root
    project_root = current.parent.parent.parent
    config_path = project_root / "config" / "config.yaml"
    
    if not config_path.exists():
        # Return defaults
        return {
            "llm": {
                "provider": "ollama",
                "model": "llama3.2",
                "base_url": "http://localhost:11434",
            },
            "qdrant": {
                "host": "localhost",
                "port": 6333,
                "collection": "failure_patterns",
            },
            "rabbitmq": {
                "host": "localhost",
                "port": 5672,
            },
            "safety": {
                "dry_run_first": True,
                "require_approval": True,
            },
        }
    
    with open(config_path) as f:
        return yaml.safe_load(f)

