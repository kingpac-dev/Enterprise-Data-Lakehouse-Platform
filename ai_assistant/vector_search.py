#!/usr/bin/env python3
"""
=============================================================================
Enterprise Data Lakehouse Platform - Vector Semantic Search Demo (M12)
=============================================================================
Demonstrates ClickHouse native vector search capabilities using Cosine Distance
and L2 Distance over enterprise runbooks, data contracts, and catalog metadata.

ClickHouse Vector SQL Equivalent:
    SELECT title, category,
           cosineDistance(vector, {query_vector}) AS distance
    FROM serving.knowledge_vectors
    ORDER BY distance ASC
    LIMIT 3;
"""

import os
import sys
import math
import argparse
import hashlib
from typing import List, Dict, Any, Tuple

# Sample Knowledge Base Corpus (Runbooks & Operations)
KNOWLEDGE_CORPUS = [
    {
        "id": "RB-01",
        "title": "Portainer Git-Backed Stack Deployment",
        "category": "DevOps / Release",
        "text": "How to deploy and update Docker Compose stacks in Portainer using Git repository polling and automated webhooks.",
        "keywords": ["portainer", "git", "stack", "deploy", "docker", "compose", "webhook"]
    },
    {
        "id": "RB-02",
        "title": "ClickHouse S3 Backup & Quarterly DR Restore Drill",
        "category": "Disaster Recovery",
        "text": "Procedures for native BACKUP to S3 object storage, verification checksums, and non-destructive restore drill testing RPO <= 1h and RTO <= 4h.",
        "keywords": ["backup", "restore", "drill", "s3", "disaster", "recovery", "rpo", "rto", "snapshot"]
    },
    {
        "id": "RB-03",
        "title": "Parts Explosion & Replication Lag Troubleshooting",
        "category": "SRE / Troubleshooting",
        "text": "Resolving 'Too many parts in all data parts in table', async_insert settings, ClickHouse Keeper Raft quorum recovery, and replication queue lag.",
        "keywords": ["parts", "explosion", "too many parts", "merge", "lag", "replication", "keeper", "raft", "read-only"]
    },
    {
        "id": "ODCS-01",
        "title": "Orders Open Data Contract Specification",
        "category": "Data Governance",
        "text": "Schema contract, nullability, allowed statuses (COMPLETED, PENDING, CANCELLED), unit_price limits, and 7 mandatory technical ingestion metadata columns.",
        "keywords": ["contract", "schema", "orders", "drift", "columns", "nullability", "rules", "metadata", "governance"]
    },
    {
        "id": "STR-01",
        "title": "Real-Time CDC & Redpanda Streaming Ingestion",
        "category": "Streaming / Real-Time",
        "text": "Sub-second event ingestion using Redpanda Kafka broker, ClickHouse Kafka table engine, and Materialized Views writing to raw.orders_landing.",
        "keywords": ["streaming", "kafka", "redpanda", "real-time", "cdc", "sub-second", "producer", "consumer", "topic"]
    }
]

DIMENSIONS = 16


def text_to_embedding(text: str) -> List[float]:
    """
    Generates a deterministic normalized dense embedding vector for demonstration.
    Uses SHA-256 seed hashing to produce realistic 16-dimensional unit vectors.
    """
    words = text.lower().replace(",", " ").replace(".", " ").split()
    vector = [0.0] * DIMENSIONS

    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).digest()
        for i in range(DIMENSIONS):
            val = (digest[i % len(digest)] / 255.0) * 2.0 - 1.0
            vector[i] += val

    # Normalize vector to unit length (L2 norm = 1.0)
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        vector = [round(x / norm, 4) for x in vector]
    return vector


def cosine_distance(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes Cosine Distance = 1.0 - Cosine Similarity (ClickHouse cosineDistance equivalent)."""
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 1.0
    sim = dot_product / (norm_a * norm_b)
    # Cosine distance is in range [0.0, 2.0]
    return round(max(0.0, 1.0 - sim), 4)


class SemanticSearchEngine:
    def __init__(self, corpus: List[Dict[str, Any]]):
        self.corpus = corpus
        # Pre-compute document embeddings
        for doc in self.corpus:
            doc["vector"] = text_to_embedding(f"{doc['title']} {doc['text']} {' '.join(doc['keywords'])}")

    def search(self, query: str, top_k: int = 3) -> List[Tuple[Dict[str, Any], float]]:
        """Searches the knowledge base using semantic cosine distance."""
        q_vec = text_to_embedding(query)
        scored_docs = []

        for doc in self.corpus:
            dist = cosine_distance(q_vec, doc["vector"])
            # Invert distance for human-friendly similarity percentage (0-100%)
            similarity_pct = round(max(0.0, (1.0 - dist / 2.0)) * 100, 1)
            scored_docs.append((doc, dist, similarity_pct))

        scored_docs.sort(key=lambda x: x[1])
        return scored_docs[:top_k]


def main():
    parser = argparse.ArgumentParser(description="ClickHouse Vector Semantic Search Demo (M12)")
    parser.add_argument("query", nargs="?", default="how to solve too many parts and replication lag", help="Search query")
    parser.add_argument("--top-k", type=int, default=3, help="Number of results to return")
    parser.add_argument("--dry-run", action="store_true", help="Run semantic search test suite")

    args = parser.parse_args()

    engine = SemanticSearchEngine(KNOWLEDGE_CORPUS)

    print("=" * 68)
    print(" ENTERPRISE CLICKHOUSE VECTOR SEMANTIC SEARCH (M12)")
    print("=" * 68)
    print(f" Search Query : \"{args.query}\"")
    print(f" Metric       : Cosine Distance (ClickHouse cosineDistance() function)")
    print(f" Dimensions   : {DIMENSIONS}-dimensional normalized dense vectors")
    print("-" * 68)

    results = engine.search(args.query, top_k=args.top_k)

    print(f"\nTOP {len(results)} SEMANTIC MATCHES:\n")
    for rank, (doc, dist, sim_pct) in enumerate(results, start=1):
        print(f"[{rank}] {doc['title']} ({doc['id']})")
        print(f"    Category  : {doc['category']}")
        print(f"    Distance  : {dist} (Cosine Similarity: {sim_pct}%)")
        print(f"    Summary   : {doc['text']}")
        print()

    print("-" * 68)
    print(" CLICKHOUSE EQUIVALENT SQL QUERY:")
    print("-" * 68)
    sample_vec = text_to_embedding(args.query)[:4]
    print(f"""SELECT
    id,
    title,
    category,
    cosineDistance(embedding, {sample_vec}...) AS distance
FROM serving.runbook_knowledge_vectors
ORDER BY distance ASC
LIMIT {args.top_k};""")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    main()
