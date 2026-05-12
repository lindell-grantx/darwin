"""v2 MVP: inference-time routing of queries to query-type buckets.

For each incoming query, embed it (Voyage-4) and find the highest-cosine
QueryTypeBucket. The chosen bucket determines which slice of the Nash
strategy to sample from. Pass 2 makes this two-axis (cross with the attacker
portfolio).

For MVP, we have one Nash strategy per generation; the routing decision is
logged for telemetry but doesn't yet weight the defender choice differently
per bucket. (Pass 1 introduces per-bucket Nash strategies.)
"""

from __future__ import annotations

import math
from typing import Sequence

from darwin.db.schemas import QueryTypeBucket


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Standard cosine. Returns 0 if either vector is the zero-vector."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def route_query_to_bucket(
    query_embedding: Sequence[float],
    buckets: Sequence[QueryTypeBucket],
) -> QueryTypeBucket:
    """Return the bucket with the highest cosine similarity to the query embedding."""
    if not buckets:
        raise ValueError("Cannot route to empty bucket list")

    best: QueryTypeBucket | None = None
    best_sim = -math.inf
    for b in buckets:
        sim = cosine_similarity(query_embedding, b.embedding)
        if sim > best_sim:
            best_sim = sim
            best = b
    assert best is not None
    return best
