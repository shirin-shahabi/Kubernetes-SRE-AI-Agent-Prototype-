"""Unit tests for cache system."""

import pytest
from pathlib import Path

from sre_agent.cache import CacheManager


class TestCacheManager:
    """Test cache manager."""
    
    def test_cache_init(self, tmp_path):
        """Test cache initialization."""
        cache = CacheManager(cache_dir=str(tmp_path))
        assert cache.cache_dir == tmp_path
    
    def test_cache_set_get(self, tmp_path):
        """Test cache set and get."""
        cache = CacheManager(cache_dir=str(tmp_path))
        
        diagnosis = {
            "root_cause": "Memory limit too low",
            "confidence": 85,
        }
        
        cache.set_diagnosis("default", "Deployment", "test-app", diagnosis)
        result = cache.get_diagnosis("default", "Deployment", "test-app")
        
        assert result is not None
        assert result["root_cause"] == "Memory limit too low"
    
    def test_cache_llm_response(self, tmp_path):
        """Test LLM response caching."""
        cache = CacheManager(cache_dir=str(tmp_path))
        
        prompt = "Test prompt"
        response = "Test response"
        
        cache.set_llm_response(prompt, response)
        cached = cache.get_llm_response(prompt)
        
        assert cached == response
    
    def test_cache_stats(self, tmp_path):
        """Test cache statistics."""
        cache = CacheManager(cache_dir=str(tmp_path))
        stats = cache.stats()
        
        assert "size" in stats
        assert "directory" in stats

