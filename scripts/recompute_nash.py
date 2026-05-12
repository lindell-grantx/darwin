#!/usr/bin/env python
"""Recompute the naive uniform Nash strategy from the Pareto front.

Reads fitness_evaluations for the latest generation, builds a (defender, difficulty)
fitness map, runs `top_k_per_bucket(k=1)` to pick the best per bucket, dedupes,
and writes a fresh NashStrategy snapshot. Intended to run as a cron job
(every K=10 generations or every N minutes).

Usage:
    MONGODB_URI=... python scripts/recompute_nash.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from darwin.db.client import close_client, get_db
from darwin.db.schemas import (
    COLLECTION_FITNESS_EVALUATIONS,
    COLLECTION_NASH_STRATEGIES,
    COLLECTION_QUERIES,
)
from darwin.evolution.nash_naive import build_uniform_strategy
from darwin.evolution.pareto_archive import top_k_per_bucket
from darwin.lib.secrets import resolve_gcp_secret


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("recompute_nash")


async def _load_query_difficulty_map(db) -> dict[str, str]:
    """Map query_id -> difficulty from the seeded queries collection.

    eval_queries.json has no `id` field — actual query IDs are Mongo
    `_id` values written during seeding (see scripts/seed_queries.py and
    scripts/seed_synthetic.py).
    """
    cursor = db[COLLECTION_QUERIES].find(
        {},
        projection={"_id": 1, "difficulty": 1},
    )
    out: dict[str, str] = {}
    async for doc in cursor:
        difficulty = doc.get("difficulty")
        if difficulty:
            out[str(doc["_id"])] = difficulty
    return out


async def main() -> None:
    if not os.environ.get("MONGODB_URI"):
        uri = resolve_gcp_secret("darwin-mongodb-uri")
        if uri:
            os.environ["MONGODB_URI"] = uri

    db = await get_db()

    # Pick the latest generation that has any fitness_evaluations
    latest_doc = await db[COLLECTION_FITNESS_EVALUATIONS].find_one(
        sort=[("generation", -1)],
        projection={"generation": 1},
    )
    if not latest_doc:
        log.warning("no fitness_evaluations found - cannot recompute")
        return
    generation = int(latest_doc["generation"])
    log.info("recomputing Nash for generation %d", generation)

    diff_map = await _load_query_difficulty_map(db)
    if not diff_map:
        log.error("no query difficulty map - queries collection empty or missing 'difficulty' fields")
        return

    # Aggregate fitness by (defender_id, difficulty)
    cursor = db[COLLECTION_FITNESS_EVALUATIONS].find({"generation": generation})
    fitness_sum: dict[tuple[str, str], float] = defaultdict(float)
    fitness_n: dict[tuple[str, str], int] = defaultdict(int)
    async for row in cursor:
        difficulty = diff_map.get(row.get("query_id"))
        if difficulty is None:
            continue
        # Use only "clean" rows (attacker_id is None) for the MVP Nash;
        # poisoned rows enter the picture in Pass 2 with PAIRED regret.
        if row.get("attacker_id") is not None:
            continue
        key = (row["genome_id"], difficulty)
        fitness_sum[key] += float(row["composite_fitness"])
        fitness_n[key] += 1

    fitness = {
        k: fitness_sum[k] / fitness_n[k]
        for k in fitness_sum
        if fitness_n[k] > 0
    }
    if not fitness:
        log.warning("no clean evaluations for gen %d - skipping", generation)
        return

    top1 = top_k_per_bucket(fitness, k=1)
    selected: list[str] = []
    for bucket, ids in top1.items():
        selected.extend(ids)
        log.info("bucket=%s top=%s", bucket, ids)

    if not selected:
        log.warning("Pareto archive empty - skipping")
        return

    strategy = build_uniform_strategy(selected, snapshot_generation=generation)
    await db[COLLECTION_NASH_STRATEGIES].insert_one(strategy.model_dump(mode="json", by_alias=True))
    log.info("wrote NashStrategy %s with %d unique defenders", strategy.id, len(strategy.weights))

    await close_client()


if __name__ == "__main__":
    asyncio.run(main())
