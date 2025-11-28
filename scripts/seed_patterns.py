#!/usr/bin/env python3
"""Seed failure patterns into Qdrant knowledge base.

Usage:
    python scripts/seed_patterns.py

This populates the vector database with known failure patterns
so the agent can match new issues against past resolutions.
"""

import uuid
from datetime import datetime, UTC

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

COLLECTION = "k8s_failure_patterns"
DIM = 384  # all-MiniLM-L6-v2 embedding dimension

# OOMKilled patterns
OOM_PATTERNS = [
    {
        "failure_type": "OOMKilled",
        "symptoms": "Pod status OOMKilled, container memory limit too low",
        "root_cause": "Container memory limit is insufficient for application workload",
        "fix": "kubectl patch deployment {name} -n {namespace} --type=json "
               "-p='[{\"op\": \"replace\", \"path\": \"/spec/template/spec/containers/0/resources/limits/memory\", \"value\": \"512Mi\"}]'",
        "risk_level": "safe",
        "scenario": "memory_limit_low",
    },
    {
        "failure_type": "OOMKilled",
        "symptoms": "Gradual memory increase, repeated OOMKilled after hours",
        "root_cause": "Application has memory leak causing gradual exhaustion",
        "fix": "Investigate application code; add restart policy as mitigation",
        "risk_level": "moderate",
        "scenario": "memory_leak",
    },
    {
        "failure_type": "OOMKilled",
        "symptoms": "JVM heap (-Xmx) exceeds container limits",
        "root_cause": "JVM heap configuration exceeds container memory limit",
        "fix": "Align JVM -Xmx to 70-80% of container memory limit",
        "risk_level": "safe",
        "scenario": "jvm_heap",
    },
]

# ServiceMisconfigured patterns
SERVICE_PATTERNS = [
    {
        "failure_type": "ServiceMisconfigured",
        "symptoms": "Service has no endpoints, kubectl get endpoints shows <none>",
        "root_cause": "Service selector does not match any pod labels",
        "fix": "kubectl patch svc {name} -n {namespace} -p '{\"spec\":{\"selector\":{\"app\":\"{correct_label}\"}}}'",
        "risk_level": "safe",
        "scenario": "label_mismatch",
    },
    {
        "failure_type": "ServiceMisconfigured",
        "symptoms": "Endpoints exist but traffic times out",
        "root_cause": "Service targetPort does not match container port",
        "fix": "kubectl patch svc {name} -n {namespace} -p '{\"spec\":{\"ports\":[{\"port\":80,\"targetPort\":{correct_port}}]}}'",
        "risk_level": "safe",
        "scenario": "port_mismatch",
    },
]


def main():
    print("Initializing FastEmbed model...")
    embedding_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")

    print("Connecting to Qdrant...")
    client = QdrantClient(host="localhost", port=6333, timeout=10, check_compatibility=False)

    # Ensure collection exists
    collections = client.get_collections().collections
    if not any(c.name == COLLECTION for c in collections):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.COSINE),
        )
        print(f"Created collection: {COLLECTION}")
    else:
        print(f"Collection exists: {COLLECTION}")

    def embed(text: str) -> list[float]:
        return list(embedding_model.embed([text]))[0].tolist()

    def pattern_to_text(pattern: dict) -> str:
        keys = ["failure_type", "symptoms", "root_cause", "fix", "scenario"]
        return " ".join(f"{k}: {pattern[k]}" for k in keys if k in pattern)

    def add_pattern(pattern: dict) -> str:
        pattern_id = str(uuid.uuid4())
        client.upsert(
            collection_name=COLLECTION,
            points=[PointStruct(
                id=pattern_id,
                vector=embed(pattern_to_text(pattern)),
                payload={**pattern, "timestamp": datetime.now(UTC).isoformat()},
            )],
        )
        return pattern_id

    # Seed patterns
    print("\n=== Seeding failure patterns ===\n")
    all_patterns = OOM_PATTERNS + SERVICE_PATTERNS
    success = 0

    for pattern in all_patterns:
        try:
            pid = add_pattern(pattern)
            print(f"[OK] {pattern['failure_type']}/{pattern['scenario']} (ID: {pid[:8]})")
            success += 1
        except Exception as e:
            print(f"[FAIL] {pattern['scenario']}: {e}")

    print(f"\n=== Seeded {success}/{len(all_patterns)} patterns ===")


if __name__ == "__main__":
    main()
