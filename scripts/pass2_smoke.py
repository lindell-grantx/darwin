#!/usr/bin/env python
"""Pass 2 verification: 50 generations of co-evolution + assertions.

Usage:
    MONGODB_URI=... python scripts/pass2_smoke.py [--n-generations 50]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from darwin.attacker.qd_archive import RISK_CATEGORIES, ATTACK_STYLES
from darwin.db.client import close_client, get_db
from darwin.db.schemas import (
    COLLECTION_ATTACKER_ARCHIVE,
    COLLECTION_GENOMES,
    COLLECTION_NASH_STRATEGIES,
)
from darwin.evolution.conductor import evolve_generation
from darwin.evolution.map_elites import behavior_descriptor
from darwin.lib.secrets import resolve_gcp_secret


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pass2_smoke")


async def _defender_cell_coverage(db) -> float:
    cursor = db[COLLECTION_GENOMES].find({"status": {"$in": ["alive", "champion"]}})
    cells: set[tuple[str, str, str]] = set()
    async for raw in cursor:
        from darwin.db.schemas import Genome
        try:
            g = Genome.model_validate(raw)
        except Exception:
            continue
        cells.add(behavior_descriptor(g))
    expected = 27  # 3 retrieval x 3 styles x 3 density buckets
    return len(cells) / expected


async def _attacker_cell_coverage(db) -> float:
    cursor = db[COLLECTION_ATTACKER_ARCHIVE].find({})
    cells: set[tuple[str, str]] = set()
    async for row in cursor:
        cells.add(tuple(row["cell_key"]))
    expected = len(RISK_CATEGORIES) * len(ATTACK_STYLES)
    return len(cells) / expected


async def _nash_convergence(db) -> float | None:
    cursor = db[COLLECTION_NASH_STRATEGIES].find(
        {}, projection={"weights": 1, "snapshot_generation": 1, "_id": 0},
    ).sort("snapshot_generation", -1).limit(2)
    snaps = await cursor.to_list(length=2)
    if len(snaps) < 2:
        return None
    a = snaps[0]["weights"]
    b = snaps[1]["weights"]
    all_keys = set(a) | set(b)
    return max(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in all_keys)


async def main(n_generations: int) -> int:
    if not os.environ.get("MONGODB_URI"):
        uri = resolve_gcp_secret("darwin-mongodb-uri")
        if uri:
            os.environ["MONGODB_URI"] = uri
    db = await get_db()
    log.info("connected; running %d generations", n_generations)

    latest = await db[COLLECTION_GENOMES].find_one(
        sort=[("generation", -1)], projection={"generation": 1}
    )
    if not latest:
        log.error("no genomes — population not seeded")
        return 2
    start = int(latest["generation"])

    for i in range(n_generations):
        try:
            await evolve_generation(db, start + i)
        except Exception as exc:
            log.warning("gen %d failed: %s", start + i, exc)
            break

    d_cov = await _defender_cell_coverage(db)
    a_cov = await _attacker_cell_coverage(db)
    nash_delta = await _nash_convergence(db)

    print()
    print("=" * 60)
    print(f"Defender cell coverage:    {d_cov:.2%}  (target >40%)")
    print(f"Attacker cell coverage:    {a_cov:.2%}  (monotonic target)")
    print(f"Nash strategy max delta:   {nash_delta if nash_delta is not None else 'N/A'}  (target <0.1)")
    print("=" * 60)

    failures = []
    if d_cov < 0.4:
        failures.append(f"defender coverage {d_cov:.2%} < 40% (MAP-Elites threshold; consider DNS fallback)")
    if nash_delta is not None and nash_delta >= 0.1:
        failures.append(f"Nash delta {nash_delta:.3f} >= 0.1 (not converged)")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        await close_client()
        return 1

    print("\nPASS")
    await close_client()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-generations", type=int, default=50)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.n_generations)))
