"""Configuration management for K8s SRE Agent."""

import os
from pathlib import Path
from typing import Any

import yaml

_config: dict[str, Any] | None = None
_config_path: Path | None = None


def find_config_file() -> Path:
    """Find the config file in standard locations."""
    search_paths = [
        Path.cwd() / "config" / "config.yaml",
        Path.cwd() / "config.yaml",
        Path(__file__).parent.parent.parent.parent.parent / "config" / "config.yaml",
        Path.home() / ".config" / "k8s-sre-agent" / "config.yaml",
    ]
    
    for path in search_paths:
        if path.exists():
            return path
    
    raise FileNotFoundError(
        f"Config file not found. Searched: {[str(p) for p in search_paths]}"
    )


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load configuration from YAML file."""
    global _config, _config_path
    
    if config_path:
        path = Path(config_path)
    else:
        path = find_config_file()
    
    _config_path = path
    
    with open(path) as f:
        _config = yaml.safe_load(f)
    
    # Override with environment variables
    _apply_env_overrides(_config)
    
    return _config


def _apply_env_overrides(config: dict[str, Any]) -> None:
    """Apply environment variable overrides to config."""
    env_mappings = {
        "OPENROUTER_API_KEY": ("llm", "api_key"),
        "OPENROUTER_MODEL": ("llm", "model"),
        "QDRANT_HOST": ("qdrant", "host"),
        "QDRANT_PORT": ("qdrant", "port"),
        "K8S_NAMESPACE": ("kubernetes", "default_namespace"),
        "LOG_LEVEL": ("logging", "level"),
    }
    
    for env_var, path in env_mappings.items():
        value = os.getenv(env_var)
        if value:
            _set_nested(config, path, value)


def _set_nested(config: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    """Set a nested config value."""
    current = config
    for key in path[:-1]:
        current = current.setdefault(key, {})
    
    # Convert port to int if needed
    if path[-1] == "port":
        value = int(value)
    
    current[path[-1]] = value


def get_config() -> dict[str, Any]:
    """Get the loaded configuration."""
    global _config
    if _config is None:
        load_config()
    return _config  # type: ignore


def get_config_value(*keys: str, default: Any = None) -> Any:
    """Get a nested config value by keys."""
    config = get_config()
    current = config
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current

