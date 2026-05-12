"""v2 MVP: extend per-generation evaluation with attacker axis.

For each (defender, query) pair, the legacy code wrote one fitness_evaluations
row. v2 MVP keeps that row (the "clean" baseline, attacker_id=None) and adds
N rows per defender per query - one per attacker - capturing the defender's
performance under each attacker's poison/injection.

Pass 2 will replace the static MVP_ATTACKERS list with an evolving attacker
population on a Lipizzaner spatial grid.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable, Optional, Sequence

from motor.motor_asyncio import AsyncIOMotorDatabase

from darwin.attacker.fixtures import MVP_ATTACKERS
from darwin.db.schemas import (
    Attacker,
    COLLECTION_ATTACKERS,
    Genome,
)


log = logging.getLogger(__name__)


def expected_row_count(*, n_defenders: int, n_attackers: int, n_queries: int) -> int:
    """Pure helper: how many fitness_evaluations rows a payoff sweep should write.

    Returns the MAX possible (assuming every attacker targets every query).
    Actual count depends on attacker.target_query_class matching query.domain_tags.
    """
    if n_defenders == 0:
        return 0
    return n_defenders * n_queries + n_defenders * n_attackers * n_queries


async def load_attackers(db: AsyncIOMotorDatabase) -> list[Attacker]:
    """Fetch all attackers from Mongo. Falls back to MVP_ATTACKERS if collection empty."""
    cursor = db[COLLECTION_ATTACKERS].find({})
    docs = await cursor.to_list(length=None)
    if not docs:
        log.warning("no attackers in DB - using MVP_ATTACKERS fixtures")
        return list(MVP_ATTACKERS)
    return [Attacker.model_validate(d) for d in docs]


EvaluateFn = Callable[
    [Genome, dict, Optional[Attacker]],
    Awaitable[float],
]

WriteFn = Callable[[list[dict]], Awaitable[None]]


async def run_payoff_for_generation(
    db: AsyncIOMotorDatabase,
    *,
    defenders: Sequence[Genome],
    queries: Sequence[dict],
    attackers: Sequence[Attacker],
    evaluate: EvaluateFn,
    generation: int,
    write_evaluations: WriteFn,
) -> int:
    """Sweep payoff matrix entries M[d, a, q] + clean rows M[d, None, q]."""
    rows: list[dict] = []

    for defender in defenders:
        for query in queries:
            # Clean baseline (no attacker)
            score = await evaluate(defender, query, None)
            rows.append({
                "genome_id": defender.id,
                "query_id": query["id"],
                "generation": generation,
                "attacker_id": None,
                "composite_fitness": float(score),
            })

            for attacker in attackers:
                if not _attacker_targets_query(attacker, query):
                    continue
                score = await evaluate(defender, query, attacker)
                rows.append({
                    "genome_id": defender.id,
                    "query_id": query["id"],
                    "generation": generation,
                    "attacker_id": attacker.id,
                    "composite_fitness": float(score),
                })

    if rows:
        await write_evaluations(rows)
    log.info("wrote %d fitness_evaluations rows for gen %d", len(rows), generation)
    return len(rows)


def _attacker_targets_query(attacker: Attacker, query: dict) -> bool:
    """Only run an attacker against a query in its target class.

    Match is exact tuple equality on `domain_tags`.
    """
    target = tuple(attacker.target_query_class)
    domain_tags = tuple(query.get("domain_tags") or [])
    return target == domain_tags
