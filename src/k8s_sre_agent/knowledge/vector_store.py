"""Simple Qdrant vector store for failure patterns."""

import uuid
from datetime import datetime
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from k8s_sre_agent.utils.config import get_config
from k8s_sre_agent.utils.logging import get_logger

logger = get_logger(__name__)


class VectorStore:
    """Qdrant vector store for failure pattern storage."""
    
    def __init__(self) -> None:
        config = get_config()
        qdrant_cfg = config.get("qdrant", {})
        
        self.host = qdrant_cfg.get("host", "localhost")
        self.port = qdrant_cfg.get("port", 6333)
        self.collection = qdrant_cfg.get("collection", "k8s_failure_patterns")
        self.dim = qdrant_cfg.get("embedding_dim", 384)
        
        self._client: QdrantClient | None = None
    
    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(host=self.host, port=self.port)
            self._ensure_collection()
        return self._client
    
    def _ensure_collection(self) -> None:
        try:
            collections = self._client.get_collections().collections
            if not any(c.name == self.collection for c in collections):
                self._client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
                )
        except Exception as e:
            logger.warning("qdrant_setup_failed", error=str(e))
    
    def add_pattern(self, pattern: dict[str, Any]) -> str:
        """Add a failure pattern."""
        pattern_id = str(uuid.uuid4())
        embedding = self._simple_embedding(pattern)
        
        try:
            self.client.upsert(
                collection_name=self.collection,
                points=[PointStruct(
                    id=pattern_id,
                    vector=embedding,
                    payload={**pattern, "timestamp": datetime.utcnow().isoformat()},
                )],
            )
            return pattern_id
        except Exception as e:
            logger.error("add_pattern_failed", error=str(e))
            return ""
    
    def search_similar(
        self,
        failure_type: str,
        context: str = "",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for similar patterns."""
        query = f"{failure_type} {context}"
        embedding = self._simple_embedding({"text": query})
        
        try:
            results = self.client.search(
                collection_name=self.collection,
                query_vector=embedding,
                limit=limit,
            )
            return [hit.payload for hit in results]
        except Exception:
            return []
    
    def _simple_embedding(self, data: dict[str, Any]) -> list[float]:
        """Generate simple hash-based embedding (placeholder for real embeddings)."""
        import hashlib
        text = str(data)
        hash_bytes = hashlib.sha384(text.encode()).digest()
        return [float(b) / 255.0 for b in hash_bytes]
