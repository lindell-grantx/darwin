"""Per-query-class Pareto front — broadens MVP's per-difficulty archive.

Each genome that wins on at least one query class gets preserved. Closer to
MAP-Elites than the MVP's 3-bucket version, but still cheaper than full
MAP-Elites cells (Pass 2).
"""

from __future__ import annotations

from collections import defaultdict


def top_k_per_query_class(
    fitness: dict[tuple[str, str], float],
    *,
    k: int,
) -> dict[str, list[str]]:
    """For each query class, return top-k defenders by fitness (descending).

    `fitness` keys are (defender_id, query_class_string). Returns
    dict[query_class -> [defender_id, ...]] of the front.
    """
    by_class: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for (defender_id, query_class), score in fitness.items():
        by_class[query_class].append((defender_id, score))

    result: dict[str, list[str]] = {}
    for cls, entries in by_class.items():
        entries.sort(key=lambda x: (-x[1], x[0]))
        result[cls] = [d for d, _ in entries[:k]]
    return result
