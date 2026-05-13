"""DGM weighted parent sampling — replaces tournament selection.

Reference: Darwin Gödel Machine (arXiv:2505.22954).
w_i = sigmoid(λ × (fitness_i − α_0)) × 1/(1 + n_children_i)
"""

from __future__ import annotations

import math
import random
from typing import Sequence

from darwin.db.schemas import Genome


def dgm_weighted_select(
    candidates: Sequence[Genome],
    n_parents: int,
    *,
    n_children_map: dict[str, int],
    lambda_: float = 10.0,
    alpha_0: float = 0.5,
    rng: random.Random,
) -> list[Genome]:
    if n_parents <= 0:
        return []
    if not candidates:
        return []

    weights: list[float] = []
    for g in candidates:
        fitness = g.fitness.composite
        n_children = n_children_map.get(g.id, 0)
        sigmoid = 1.0 / (1.0 + math.exp(-lambda_ * (fitness - alpha_0)))
        novelty = 1.0 / (1.0 + n_children)
        weights.append(sigmoid * novelty)

    return rng.choices(list(candidates), weights=weights, k=n_parents)


async def count_children_per_genome(
    db, generation_window: int = 5,
) -> dict[str, int]:
    """Aggregate n_children per genome from the last N generations."""
    from darwin.db.schemas import COLLECTION_GENOMES

    latest_doc = await db[COLLECTION_GENOMES].find_one(sort=[("generation", -1)], projection={"generation": 1})
    if not latest_doc:
        return {}
    latest_gen = int(latest_doc["generation"])
    floor = max(0, latest_gen - generation_window)

    pipeline = [
        {"$match": {"generation": {"$gte": floor}}},
        {"$unwind": "$parent_ids"},
        {"$group": {"_id": "$parent_ids", "n": {"$sum": 1}}},
    ]
    result: dict[str, int] = {}
    async for row in db[COLLECTION_GENOMES].aggregate(pipeline):
        result[row["_id"]] = int(row["n"])
    return result
