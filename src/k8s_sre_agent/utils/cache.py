"""Caching system for diagnosis results and LLM responses."""

import hashlib
import json
from pathlib import Path
from typing import Any

import diskcache

from k8s_sre_agent.utils.logging import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Cache manager for SRE Agent with disk-based persistence."""
    
    def __init__(
        self,
        cache_dir: str = ".cache",
        diagnosis_ttl: int = 3600,
        llm_ttl: int = 7200,
    ) -> None:
        """Initialize cache with configurable TTLs."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.diagnosis_ttl = diagnosis_ttl
        self.llm_ttl = llm_ttl
        
        self._cache = diskcache.Cache(str(self.cache_dir / "sre_agent"))
        logger.info("cache_initialized", directory=str(self.cache_dir))
    
    def _make_key(self, *parts: str, prefix: str = "") -> str:
        """Generate a cache key from parts."""
        key_str = ":".join(parts)
        hashed = hashlib.sha256(key_str.encode()).hexdigest()[:16]
        return f"{prefix}:{hashed}" if prefix else hashed
    
    def get_diagnosis(
        self,
        namespace: str,
        resource_type: str,
        resource_name: str,
    ) -> dict[str, Any] | None:
        """Get cached diagnosis result."""
        key = self._make_key(namespace, resource_type, resource_name, prefix="diagnosis")
        result = self._cache.get(key)
        
        if result:
            logger.debug("cache_hit", key_type="diagnosis", resource=resource_name)
        
        return result
    
    def set_diagnosis(
        self,
        namespace: str,
        resource_type: str,
        resource_name: str,
        diagnosis: dict[str, Any],
    ) -> None:
        """Cache diagnosis result."""
        key = self._make_key(namespace, resource_type, resource_name, prefix="diagnosis")
        self._cache.set(key, diagnosis, expire=self.diagnosis_ttl)
        logger.debug("cache_set", key_type="diagnosis", resource=resource_name)
    
    def get_llm_response(self, prompt_hash: str) -> str | None:
        """Get cached LLM response by prompt hash."""
        key = f"llm:{prompt_hash}"
        result = self._cache.get(key)
        
        if result:
            logger.debug("cache_hit", key_type="llm")
        
        return result
    
    def set_llm_response(self, prompt_hash: str, response: str) -> None:
        """Cache LLM response."""
        key = f"llm:{prompt_hash}"
        self._cache.set(key, response, expire=self.llm_ttl)
        logger.debug("cache_set", key_type="llm")
    
    def get_pattern(self, failure_type: str, signature: str) -> dict[str, Any] | None:
        """Get cached failure pattern."""
        key = self._make_key(failure_type, signature, prefix="pattern")
        return self._cache.get(key)
    
    def set_pattern(
        self,
        failure_type: str,
        signature: str,
        pattern: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """Cache failure pattern."""
        key = self._make_key(failure_type, signature, prefix="pattern")
        self._cache.set(key, pattern, expire=ttl or self.diagnosis_ttl)
    
    def invalidate(
        self,
        namespace: str,
        resource_type: str,
        resource_name: str,
    ) -> None:
        """Invalidate cached diagnosis for a resource."""
        key = self._make_key(namespace, resource_type, resource_name, prefix="diagnosis")
        self._cache.delete(key)
        logger.debug("cache_invalidated", resource=resource_name)
    
    def clear(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        logger.info("cache_cleared")
    
    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "directory": str(self.cache_dir),
            "volume": self._cache.volume(),
        }
    
    def close(self) -> None:
        """Close the cache."""
        self._cache.close()

