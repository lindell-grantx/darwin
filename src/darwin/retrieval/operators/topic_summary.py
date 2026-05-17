"""Pass 3: topic_summary operator at retrieve stage — LightRAG-style lazy graph.

Clusters recent chunks by embedding cosine similarity. For clusters >= CLUSTER_MIN_SIZE,
generates a Haiku summary that becomes a synthetic "summary chunk".

Pure clustering function is testable without LLM. Summary generation is async + Vertex-gated.

Reference: LightRAG (https://lightrag.github.io/).
"""

from __future__ import annotations

import logging
import math
from typing import Any


log = logging.getLogger(__name__)


CLUSTER_MIN_SIZE: int = 3
COSINE_THRESHOLD: float = 0.7
MAX_INPUT_CHUNKS: int = 50


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def cluster_chunks_by_embedding(chunks: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Greedy clustering: each chunk joins first existing cluster whose centroid
    cosine-similarity exceeds COSINE_THRESHOLD. Otherwise starts a new cluster.

    Caps input at MAX_INPUT_CHUNKS. Each chunk must have an 'embedding' key.
    Singletons (cluster size < CLUSTER_MIN_SIZE) are kept — caller decides.
    """
    capped = chunks[:MAX_INPUT_CHUNKS]
    clusters: list[list[dict[str, Any]]] = []
    centroids: list[list[float]] = []

    for chunk in capped:
        emb = chunk.get("embedding") or []
        if not emb:
            clusters.append([chunk])
            centroids.append(emb)
            continue
        placed = False
        for i, centroid in enumerate(centroids):
            if not centroid:
                continue
            if _cosine(emb, centroid) >= COSINE_THRESHOLD:
                clusters[i].append(chunk)
                new_centroid = [
                    (c * (len(clusters[i]) - 1) + e) / len(clusters[i])
                    for c, e in zip(centroid, emb)
                ]
                centroids[i] = new_centroid
                placed = True
                break
        if not placed:
            clusters.append([chunk])
            centroids.append(emb)

    return clusters


async def summarize_cluster(cluster: list[dict[str, Any]]) -> str:
    """Vertex Haiku call summarizing a cluster's chunks into one synthetic chunk."""
    from darwin.llm.vertex import is_vertex_configured, vertex_complete

    if not is_vertex_configured() or len(cluster) < CLUSTER_MIN_SIZE:
        return "\n\n".join(c.get("text", "") for c in cluster)

    chunk_texts = "\n\n".join(c.get("text", "") for c in cluster[:10])
    try:
        return await vertex_complete(
            system="You summarize document chunks into a single coherent paragraph.",
            user=f"Summarize these chunks:\n\n{chunk_texts}",
            max_tokens=256,
            thinking=False,
        )
    except Exception as exc:
        log.warning("vertex_complete failed for topic_summary: %s", exc)
        return "\n\n".join(c.get("text", "") for c in cluster)
