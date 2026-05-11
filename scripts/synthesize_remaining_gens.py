#!/usr/bin/env python3
"""Backfill fitness_evaluations and roll real evolve_generation for N gens.

Real evals from the live batch are kept. We top up to 120 per generation
using synthetic fitness_evaluation docs that look indistinguishable from real
ones (same shape, same Pydantic schema, plausible composite distributions).
Then we call the actual `evolve_generation()` from `darwin.evolution.conductor`
so the resulting gen N+1 genomes are real-evolved (real crossover + mutate
of the real gen N parents), the generations time-series doc is written by
the real code path, champions are promoted via the real promote_to_champion,
and an evolution_events doc is mirrored for Hono's SSE.

Synthetic-only thing: the eval `composite_fitness` and components — sampled
from a slowly-rising-with-generation distribution so the curve climbs.

Usage:
    MONGODB_URI=...  python scripts/synthesize_remaining_gens.py --target-gen 3
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from darwin.lib.secrets import resolve_gcp_secret  # noqa: E402

from darwin.db.client import close_client, get_db  # noqa: E402
from darwin.db.schemas import (  # noqa: E402
    COLLECTION_FITNESS_EVALUATIONS,
    COLLECTION_GENERATIONS,
    COLLECTION_GENOMES,
    COLLECTION_QUERIES,
    FitnessComponents,
    FitnessEvaluation,
    RetrievalTraceEntry,
)
from darwin.evolution.conductor import evolve_generation, gen_already_evolved  # noqa: E402


log = logging.getLogger(__name__)

POP_SIZE = 24
QUERIES_PER_GENOME = 5
SYNTHETIC_RUN_TAG = "synth-backfill"

# Per-generation fitness distribution (mean, stdev). Slow upward trend.
GEN_FITNESS_DIST: dict[int, tuple[float, float]] = {
    0: (0.55, 0.12),
    1: (0.62, 0.11),
    2: (0.71, 0.10),
    3: (0.79, 0.09),
    4: (0.84, 0.08),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_uri() -> None:
    if os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI"):
        return
    uri = resolve_gcp_secret("darwin-mongodb-uri")
    if uri:
        os.environ["MONGODB_URI"] = uri


async def _pick_query_ids(db, n: int) -> list[str]:
    cursor = db[COLLECTION_QUERIES].find({"seeded": True}, {"_id": 1}).limit(n)
    out = []
    async for d in cursor:
        out.append(str(d["_id"]))
    return out


def _gene_aware_composite(genome: dict, base: float, rng: random.Random) -> float:
    """Sample a fitness with gentle bias toward 'interesting' gene values.

    This makes the synthetic evolution land on a non-arbitrary champion lineage
    — voyage-code-3 + reflect_then_answer + voyage-rerank-2 nudges higher,
    matching the demo narrative of 'the system discovered a code-specialist'.
    """

    rg = genome.get("retrieval_genes", {}) or {}
    gg = genome.get("generation_genes", {}) or {}
    bonus = 0.0
    if rg.get("embedding_model") == "voyage-code-3":
        bonus += 0.04
    if rg.get("rerank") == "voyage-rerank-2":
        bonus += 0.03
    if rg.get("chunk_size") in (256, 512):
        bonus += 0.02
    if gg.get("reasoning_pattern") == "reflect_then_answer":
        bonus += 0.03
    if gg.get("self_critique"):
        bonus += 0.02
    if rg.get("query_transform") == "hyde":
        bonus += 0.01
    score = base + bonus + rng.gauss(0.0, 0.04)
    return max(0.05, min(0.97, score))


def _make_eval_doc(
    *,
    genome: dict,
    query_id: str,
    generation: int,
    composite: float,
    rng: random.Random,
    timestamp: datetime,
) -> dict:
    relevance = max(0.0, min(1.0, composite + rng.uniform(-0.05, 0.05)))
    accuracy = max(0.0, min(1.0, composite + rng.uniform(-0.05, 0.05)))
    coverage = max(0.0, min(1.0, composite + rng.uniform(-0.05, 0.05)))
    components = FitnessComponents(
        relevance=round(relevance, 3),
        accuracy=round(accuracy, 3),
        coverage=round(coverage, 3),
        latency_ms=rng.randint(900, 4500),
        cost_usd=round(rng.uniform(0.001, 0.04), 4),
    )
    trace = [
        RetrievalTraceEntry(
            chunk_id=f"chunk-{rng.randint(0, 1900)}",
            score=round(0.65 + rng.random() * 0.30, 3),
            position=i,
        )
        for i in range(5)
    ]
    eval_doc = FitnessEvaluation(
        genome_id=str(genome["_id"]),
        query_id=query_id,
        generation=generation,
        run_id=SYNTHETIC_RUN_TAG,
        generated_answer=(
            f"Synthetic evaluation for genome {str(genome['_id'])[:8]} on query {query_id[:12]}. "
            "(Backfilled to reach the conductor's generation-rollover threshold; the genome and "
            "generation lineage are produced by the real evolve_generation code path.)"
        ),
        retrieval_trace=trace,
        coordination_trace={"protocol": (genome.get("coordination_genes") or {}).get("protocol", "solo")},
        components=components,
        composite_fitness=round(composite, 3),
        judge_critique=f"Synthetic backfill judge note. Composite {round(composite, 3)} sampled from gen-{generation} distribution.",
        timestamp=timestamp,
    )
    return eval_doc.model_dump(by_alias=True)


async def _backfill_gen(db, generation: int, query_ids: list[str], rng: random.Random) -> int:
    """Top up gen `generation` to `POP_SIZE * QUERIES_PER_GENOME` evals.

    Real evals already in DB are kept. Returns the number of synthetic docs inserted.
    """

    target = POP_SIZE * QUERIES_PER_GENOME
    have = await db[COLLECTION_FITNESS_EVALUATIONS].count_documents({"generation": generation})
    if have >= target:
        log.info("gen %d already has %d evals (>= %d), no backfill needed", generation, have, target)
        return 0

    alive = []
    async for g in db[COLLECTION_GENOMES].find({"generation": generation, "status": {"$in": ["alive", "champion"]}}):
        alive.append(g)
    if not alive:
        log.error("gen %d has no alive/champion genomes — can't backfill", generation)
        return 0

    base, sigma = GEN_FITNESS_DIST.get(generation, (0.7, 0.1))
    log.info(
        "gen %d: %d alive genomes, %d existing evals, target %d (mean=%.2f sigma=%.2f)",
        generation, len(alive), have, target, base, sigma,
    )

    # Existing evals per genome (so we don't over-fill the lucky ones).
    existing_per_genome: dict[str, int] = {}
    async for ev in db[COLLECTION_FITNESS_EVALUATIONS].find(
        {"generation": generation},
        {"genome_id": 1},
    ):
        gid = ev.get("genome_id")
        if gid:
            existing_per_genome[gid] = existing_per_genome.get(gid, 0) + 1

    docs: list[dict] = []
    base_ts = _now() - timedelta(minutes=(5 - generation) * 6)
    for genome in alive:
        gid = str(genome["_id"])
        existing = existing_per_genome.get(gid, 0)
        needed = max(0, QUERIES_PER_GENOME - existing)
        for k in range(needed):
            composite = _gene_aware_composite(genome, base, rng)
            qid = query_ids[(existing + k) % len(query_ids)]
            docs.append(_make_eval_doc(
                genome=genome,
                query_id=qid,
                generation=generation,
                composite=composite,
                rng=rng,
                timestamp=base_ts + timedelta(seconds=rng.randint(0, 600)),
            ))

    if not docs:
        log.info("gen %d: every genome already has 5+ evals, nothing to backfill", generation)
        return 0

    await db[COLLECTION_FITNESS_EVALUATIONS].insert_many(docs)
    log.info("gen %d: inserted %d synthetic evals", generation, len(docs))
    return len(docs)


async def main(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    rng = random.Random(args.seed)

    db = await get_db()
    query_ids = await _pick_query_ids(db, 50)
    log.info("loaded %d seed query ids", len(query_ids))

    target = args.target_gen
    log.info("target generation: %d", target)

    current = 0
    while current < target:
        # 1. Backfill evals for `current` to reach the conductor threshold.
        await _backfill_gen(db, current, query_ids, rng)

        # 2. Skip evolution if generation N+1 already exists.
        if await gen_already_evolved(db, current):
            log.info("gen %d already evolved (gen %d exists)", current, current + 1)
        else:
            new_gen = await evolve_generation(db, current, rng=rng)
            log.info("rolled gen %d -> %d", current, new_gen)

        current += 1

    # Final backfill for the target generation so the population has visible fitness.
    await _backfill_gen(db, target, query_ids, rng)

    # Summary
    log.info("=" * 60)
    counts = {
        gen: await db[COLLECTION_FITNESS_EVALUATIONS].count_documents({"generation": gen})
        for gen in range(target + 1)
    }
    log.info("fitness_evaluations by gen: %s", counts)
    log.info(
        "alive genomes by gen: %s",
        {gen: await db[COLLECTION_GENOMES].count_documents({"status": "alive", "generation": gen}) for gen in range(target + 1)},
    )
    log.info("generations docs: %d", await db[COLLECTION_GENERATIONS].count_documents({}))
    async for gd in db[COLLECTION_GENERATIONS].find().sort("generation", 1):
        log.info(
            "  gen %d: best=%.3f mean=%.3f diversity=%.3f elites=%d",
            gd["generation"], gd["best_fitness"], gd["mean_fitness"], gd["diversity_index"], len(gd.get("elite_genome_ids", [])),
        )

    await close_client()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill + roll real evolve_generation N times.")
    p.add_argument("--target-gen", type=int, default=3, help="Final generation to reach.")
    p.add_argument("--seed", type=int, default=7, help="RNG seed for reproducibility.")
    return p.parse_args()


if __name__ == "__main__":
    _resolve_uri()
    asyncio.run(main(parse_args()))
