#!/usr/bin/env python
"""Pass 1 verification: 30 generations of evolution + assertions on outcomes.

Reads from existing seeded population (genomes, queries, attackers). Triggers
30 generation rollovers (or as many as fit in budget). Then computes:

1. Cell coverage: fraction of (query_class, archive position) cells populated. Must stay >50%.
2. GEPA lift: mean composite_fitness of reflective-mutated offspring vs mechanical-mutated.
   (Placeholder until mutation metadata is recorded.)
3. MADE non-degeneracy: pairwise correlation of predicate vector axes. Max corr must be <0.95.

Usage:
    MONGODB_URI=... python scripts/pass1_smoke.py [--n-generations 30]
"""

from __future__ import annotations

import argparse
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
    COLLECTION_GENERATIONS,
    COLLECTION_GENOMES,
    COLLECTION_QUERIES,
)
from darwin.evolution.conductor import evolve_generation
from darwin.evolution.per_query_class import top_k_per_query_class
from darwin.fitness.made_rubric import MADE_PREDICATES
from darwin.lib.secrets import resolve_gcp_secret


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pass1_smoke")


async def _cell_coverage(db) -> float:
    """Fraction of (query_class, top-K position) cells with at least one defender."""
    latest_doc = await db[COLLECTION_GENERATIONS].find_one(
        sort=[("generation", -1)], projection={"generation": 1}
    )
    if not latest_doc:
        return 0.0
    gen = int(latest_doc["generation"])

    diff_map: dict[str, str] = {}
    async for q in db[COLLECTION_QUERIES].find({}, projection={"_id": 1, "domain_tags": 1}):
        diff_map[str(q["_id"])] = ",".join(q.get("domain_tags") or [])

    fitness_sum: dict[tuple[str, str], float] = defaultdict(float)
    fitness_n: dict[tuple[str, str], int] = defaultdict(int)
    async for row in db[COLLECTION_FITNESS_EVALUATIONS].find({"generation": gen, "attacker_id": None}):
        cls = diff_map.get(row.get("query_id"))
        if not cls:
            continue
        fitness_sum[(row["genome_id"], cls)] += float(row["composite_fitness"])
        fitness_n[(row["genome_id"], cls)] += 1
    fitness = {k: fitness_sum[k] / fitness_n[k] for k in fitness_sum if fitness_n[k] > 0}
    if not fitness:
        return 0.0

    archive = top_k_per_query_class(fitness, k=3)
    n_query_classes = len(set(diff_map.values()))
    expected_cells = n_query_classes * 3
    populated_cells = sum(len(ids) for ids in archive.values())
    return populated_cells / max(1, expected_cells)


async def _made_max_correlation(db) -> float | None:
    """Max pairwise Pearson correlation across MADE predicate axes over recent evals."""
    cursor = db[COLLECTION_FITNESS_EVALUATIONS].find(
        {"attacker_id": None},
        projection={"components": 1, "_id": 0},
    ).limit(500)
    rows = await cursor.to_list(length=500)
    if len(rows) < 30:
        return None

    vectors: dict[str, list[float]] = {p: [] for p in MADE_PREDICATES}
    for r in rows:
        comp = r.get("components") or {}
        for p in MADE_PREDICATES:
            vectors[p].append(float(comp.get(p, 0.5)))

    import statistics
    max_corr = 0.0
    keys = list(MADE_PREDICATES)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a = vectors[keys[i]]
            b = vectors[keys[j]]
            if not a or not b or statistics.pstdev(a) == 0 or statistics.pstdev(b) == 0:
                continue
            n = len(a)
            mean_a = statistics.mean(a)
            mean_b = statistics.mean(b)
            cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b)) / n
            corr = cov / (statistics.pstdev(a) * statistics.pstdev(b))
            max_corr = max(max_corr, abs(corr))
    return max_corr


async def main(n_generations: int) -> int:
    if not os.environ.get("MONGODB_URI"):
        uri = resolve_gcp_secret("darwin-mongodb-uri")
        if uri:
            os.environ["MONGODB_URI"] = uri

    db = await get_db()
    log.info("connected; running %d generations", n_generations)

    latest_doc = await db[COLLECTION_GENOMES].find_one(
        sort=[("generation", -1)], projection={"generation": 1}
    )
    if not latest_doc:
        log.error("no genomes found - population not seeded")
        return 2

    start = int(latest_doc["generation"])
    for i in range(n_generations):
        gen = start + i
        try:
            await evolve_generation(db, gen)
        except Exception as exc:
            log.warning("evolve gen %d failed: %s", gen, exc)
            break

    coverage = await _cell_coverage(db)
    max_corr = await _made_max_correlation(db)

    print()
    print("=" * 60)
    print(f"Cell coverage:           {coverage:.2%}  (target >50%)")
    print(f"GEPA lift vs mechanical: N/A (metadata recording is Pass 2 work)")
    print(f"MADE max pairwise corr:  {max_corr if max_corr is not None else 'N/A (insufficient data)'}  (target <0.95)")
    print("=" * 60)

    failures = []
    if coverage < 0.5:
        failures.append(f"cell coverage {coverage:.2%} < 50%")
    if max_corr is not None and max_corr >= 0.95:
        failures.append(f"MADE max correlation {max_corr:.3f} >= 0.95 (degenerate)")

    if failures:
        print()
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        await close_client()
        return 1

    print()
    print("PASS")
    await close_client()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-generations", type=int, default=30)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.n_generations)))
