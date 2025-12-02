"""Caching system for diagnosis results and LLM responses."""

import hashlib
import json
from pathlib import Path

import diskcache

from sre_agent.utils import get_logger, load_config

logger = get_logger(__name__)
config = load_config()


class CacheManager:
    """Cache manager for SRE Agent."""
    
    def __init__(self, cache_dir: str = ".cache"):
        """Initialize cache."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Use diskcache for persistent caching
        self.cache = diskcache.Cache(str(self.cache_dir / "sre_agent_cache"))
        logger.info(f"Cache initialized: {self.cache_dir}")
    
    def _make_key(self, namespace: str, resource_type: str, resource_name: str, stage: str = "") -> str:
        """Generate cache key."""
        key_str = f"{namespace}:{resource_type}:{resource_name}:{stage}"
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get_diagnosis(self, namespace: str, resource_type: str, resource_name: str) -> dict | None:
        """Get cached diagnosis."""
        key = self._make_key(namespace, resource_type, resource_name, "diagnosis")
        result = self.cache.get(key)
        if result:
            logger.info("Cache hit: diagnosis")
        return result
    
    def set_diagnosis(self, namespace: str, resource_type: str, resource_name: str, diagnosis: dict):
        """Cache diagnosis result."""
        key = self._make_key(namespace, resource_type, resource_name, "diagnosis")
        self.cache.set(key, diagnosis, expire=3600)  # 1 hour expiry
        logger.info("Cached diagnosis")
    
    def get_llm_response(self, prompt: str) -> str | None:
        """Get cached LLM response."""
        key = hashlib.sha256(prompt.encode()).hexdigest()
        result = self.cache.get(f"llm:{key}")
        if result:
            logger.info("Cache hit: LLM response")
        return result
    
    def set_llm_response(self, prompt: str, response: str):
        """Cache LLM response."""
        key = hashlib.sha256(prompt.encode()).hexdigest()
        self.cache.set(f"llm:{key}", response, expire=7200)  # 2 hour expiry
        logger.info("Cached LLM response")
    
    def clear(self):
        """Clear all cache."""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "directory": str(self.cache_dir),
        }

