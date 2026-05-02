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

    raise NotImplementedError("B3: implement tournament_select")


def elite_select(candidates: list[Genome], k: int) -> list[Genome]:
    """Top-`k` candidates by `fitness.composite` (descending), tie-break by id.

    Pure / deterministic: same input → same output. Returns at most `k`.
    """

    raise NotImplementedError("B3: implement elite_select")


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

    raise NotImplementedError("B3: implement aggregate_mean_fitness_by_generation")
