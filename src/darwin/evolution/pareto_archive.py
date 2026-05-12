"""v2 MVP: Pareto-front archive over difficulty buckets.

Replaces 'single best champion' with 'best per difficulty bucket'. A defender
that excels on hard queries but is mediocre on easy ones survives — addresses
the OOD-specialist preservation goal without the full MAP-Elites machinery
(which lands in Pass 2).

The archive is a dict[bucket -> list[defender_id]]. Pass 1 will broaden this
to per-query-class fronts. Pass 2 replaces it with proper MAP-Elites cells.
"""

from __future__ import annotations

import logging
from collections import defaultdict


log = logging.getLogger(__name__)


DIFFICULTY_BUCKETS: tuple[str, ...] = ("easy", "medium", "hard")


def pareto_front_per_bucket(
    fitness: dict[tuple[str, str], float],
) -> dict[str, list[str]]:
    """For each difficulty bucket, return all defenders tied for max fitness.

    `fitness` maps (defender_id, difficulty) -> mean fitness on that bucket.
    Returns dict[difficulty -> [defender_id, ...]] of the front (max-tied set).
    """
    by_bucket: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for (defender_id, bucket), score in fitness.items():
        if bucket in DIFFICULTY_BUCKETS:
            by_bucket[bucket].append((defender_id, score))

    front: dict[str, list[str]] = {}
    for bucket in DIFFICULTY_BUCKETS:
        entries = by_bucket.get(bucket, [])
        if not entries:
            front[bucket] = []
            continue
        max_score = max(s for _, s in entries)
        front[bucket] = [d for d, s in entries if s == max_score]
    return front


def top_k_per_bucket(
    fitness: dict[tuple[str, str], float],
    *,
    k: int,
) -> dict[str, list[str]]:
    """For each difficulty bucket, return top-k defenders by fitness (descending)."""
    by_bucket: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for (defender_id, bucket), score in fitness.items():
        if bucket in DIFFICULTY_BUCKETS:
            by_bucket[bucket].append((defender_id, score))

    result: dict[str, list[str]] = {}
    for bucket in DIFFICULTY_BUCKETS:
        entries = by_bucket.get(bucket, [])
        entries.sort(key=lambda x: (-x[1], x[0]))
        result[bucket] = [d for d, _ in entries[:k]]
    return result
