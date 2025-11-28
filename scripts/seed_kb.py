"""Seed Qdrant knowledge base with initial failure patterns."""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from sre_agent.utils import get_logger, load_config

logger = get_logger(__name__)
config = load_config()


def seed_knowledge_base():
    """Seed Qdrant with initial failure patterns."""
    client = QdrantClient(
        host=config["qdrant"]["host"],
        port=config["qdrant"]["port"],
    )
    
    collection = config["qdrant"]["collection"]
    
    # Ensure collection exists
    try:
        collections = client.get_collections().collections
        if not any(c.name == collection for c in collections):
            client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(
                    size=768,  # nomic-embed-text dimension
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created collection: {collection}")
    except Exception as e:
        logger.error(f"Could not create collection: {e}")
        return
    
    # Seed with basic patterns
    patterns = [
        {
            "id": "oom-001",
            "failure_type": "OOMKilled",
            "description": "Memory limit too low",
            "root_cause": "Container memory limit configured lower than application baseline requirement",
            "fix": "kubectl patch deployment {name} -n {namespace} --type='json' -p='[{\"op\": \"replace\", \"path\": \"/spec/template/spec/containers/0/resources/limits/memory\", \"value\": \"512Mi\"}]'",
            "confidence": 0.9,
        },
        {
            "id": "svc-001",
            "failure_type": "ServiceMisconfigured",
            "description": "Service selector mismatch",
            "root_cause": "Service selector labels do not match pod labels",
            "fix": "kubectl patch svc {name} -n {namespace} --type='json' -p='[{\"op\": \"replace\", \"path\": \"/spec/selector\", \"value\": {correct_labels}}]'",
            "confidence": 0.95,
        },
    ]
    
    # For now, store as payloads (embeddings would be generated in production)
    for pattern in patterns:
        try:
            client.upsert(
                collection_name=collection,
                points=[{
                    "id": hash(pattern["id"]),
                    "vector": [0.0] * 768,  # Placeholder - would use real embeddings
                    "payload": pattern,
                }]
            )
            logger.info(f"Seeded pattern: {pattern['id']}")
        except Exception as e:
            logger.warning(f"Could not seed pattern {pattern['id']}: {e}")
    
    logger.info("Knowledge base seeding complete")


if __name__ == "__main__":
    seed_knowledge_base()

