"""Pure selection functions + Mongo aggregation for per-genome fitness rollup."""

from __future__ import annotations

import random
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from darwin.db.schemas import Genome


__all__ = [
    "aggregate_mean_fitness_by_generation",
    "elite_select",
    "tournament_select",
]


def tournament_select(
    candidates: list[Genome],
    k: int,
    *,
    tournament_size: int = 3,
    rng: Optional[random.Random] = None,
) -> list[Genome]:
    """Pick `k` parents via repeated tournaments of `tournament_size`.

    Each tournament: sample `tournament_size` random candidates with
    replacement, keep the one with highest `fitness.composite`. Return `k`
    distinct (by id) winners — if duplicates emerge, re-sample. Caller
    guarantees `len(candidates) >= tournament_size`.
    """

    if k <= 0:
        return []
    rng = rng if rng is not None else random.Random()

    winners: list[Genome] = []
    chosen_ids: set[str] = set()
    pool_size = len({g.id for g in candidates})
    while len(winners) < k:
        sampled = [rng.choice(candidates) for _ in range(tournament_size)]
        winner = max(sampled, key=lambda g: g.fitness.composite)
        # Once we've exhausted the distinct-id pool, allow duplicate winners so
        # the loop always terminates — standard tournament selection lets a fit
        # parent mate more than once.
        if winner.id in chosen_ids and len(chosen_ids) < pool_size:
            continue
        winners.append(winner)
        chosen_ids.add(winner.id)
    return winners


def elite_select(candidates: list[Genome], k: int) -> list[Genome]:
    """Top-`k` candidates by `fitness.composite` (descending), tie-break by id.

    Pure / deterministic: same input → same output. Returns at most `k`.
    """

    if k <= 0:
        return []
    ordered = sorted(candidates, key=lambda g: (-g.fitness.composite, g.id))
    return ordered[:k]


async def aggregate_mean_fitness_by_generation(
    db: AsyncIOMotorDatabase,
    generation: int,
) -> dict[str, float]:
    """Aggregate `fitness_evaluations` for `generation` → {genome_id: mean composite}.

    Use a Mongo `$group` pipeline:
        [{$match: {generation}}, {$group: {_id: "$genome_id", mean: {$avg: "$composite_fitness"}, n: {$sum: 1}}}]

    Return a dict keyed by genome_id. Genomes with zero evaluations in this
    generation are absent from the dict (caller decides how to handle them —
    typically defaults to 0.0).
    """

    pipeline = [
        {"$match": {"generation": generation}},
        {
            "$group": {
                "_id": "$genome_id",
                "mean": {"$avg": "$composite_fitness"},
                "n": {"$sum": 1},
            }
        },
    ]
    result: dict[str, float] = {}
    async for doc in db["fitness_evaluations"].aggregate(pipeline):
        result[doc["_id"]] = float(doc["mean"])
    return result
