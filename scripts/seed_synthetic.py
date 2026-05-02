#!/usr/bin/env python3
"""Seed synthetic evolution data for Andrey's backend to test against.

Generates 4 generations (0..3) with 24 genomes each, parent_ids chained,
fitness_evaluations across all (genome, query) pairs, generation summary docs
showing realistic upward fitness trends, and 2 champions.

Idempotent: marks all docs with `notes: "synthetic"` and wipes them before
re-seeding when run with --replace.

Usage:
    MONGODB_URI=... python scripts/seed_synthetic.py --replace

Counts after a clean run:
    genomes:               96  (24 alive at gen 3, 72 retired across gens 0-2)
    generations:            4  (gens 0..3 — gen 0 is the seeded "initial state")
    fitness_evaluations:  480  (24 genomes × 5 queries × 4 gens — ~minus gen-0 if you skip)
    champions:              2
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import random
import statistics
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from darwin.db.client import close_client, get_db  # noqa: E402
from darwin.db.schemas import (  # noqa: E402
    COLLECTION_CHAMPIONS,
    COLLECTION_FITNESS_EVALUATIONS,
    COLLECTION_GENERATIONS,
    COLLECTION_GENOMES,
    Champion,
    FitnessComponents,
    FitnessEvaluation,
    FitnessSummary,
    Genome,
    RetrievalTraceEntry,
)
from darwin.genome.crossover import uniform_crossover  # noqa: E402
from darwin.genome.factory import random_population  # noqa: E402
from darwin.genome.mutate import mutate  # noqa: E402
from darwin.genome.types import gene_distance  # noqa: E402


log = logging.getLogger(__name__)


SYNTHETIC_NOTE = "synthetic"
POP_SIZE = 24
ELITE_K = 4
N_GENERATIONS = 4  # gen 0..3
QUERIES_PER_GEN = 5
MUTATION_RATE = 0.15

# Fitness trends upward across generations to make the curve look like real evolution.
GEN_FITNESS_RANGES: dict[int, tuple[float, float]] = {
    0: (0.20, 0.55),
    1: (0.30, 0.65),
    2: (0.42, 0.74),
    3: (0.55, 0.83),
}


def _trace(rng: random.Random, n: int = 5) -> list[RetrievalTraceEntry]:
    return [
        RetrievalTraceEntry(
            chunk_id=f"synthetic-chunk-{rng.randint(0, 999)}",
            score=round(0.6 + rng.random() * 0.4, 3),
            position=i,
        )
        for i in range(n)
    ]


def _components(composite: float, rng: random.Random) -> FitnessComponents:
    jitter = lambda: max(0.0, min(1.0, composite + rng.uniform(-0.08, 0.08)))
    return FitnessComponents(
        relevance=round(jitter(), 3),
        accuracy=round(jitter(), 3),
        coverage=round(jitter(), 3),
        latency_ms=rng.randint(800, 4500),
        cost_usd=round(rng.uniform(0.002, 0.045), 4),
    )


async def _fetch_query_ids(db) -> list[str]:
    cursor = db["queries"].find({}, {"_id": 1}).limit(QUERIES_PER_GEN * 4)
    ids: list[str] = []
    async for doc in cursor:
        ids.append(str(doc["_id"]))
    if len(ids) < QUERIES_PER_GEN:
        log.warning(
            "queries collection has only %d entries; padding with placeholder ids",
            len(ids),
        )
        ids.extend(f"synthetic-query-{i}" for i in range(QUERIES_PER_GEN - len(ids)))
    return ids


async def _wipe_synthetic(db) -> None:
    g = await db[COLLECTION_GENOMES].delete_many({"notes": SYNTHETIC_NOTE})
    f = await db[COLLECTION_FITNESS_EVALUATIONS].delete_many({"run_id": SYNTHETIC_NOTE})
    gn = await db[COLLECTION_GENERATIONS].delete_many({"selection": "synthetic"})
    c = await db[COLLECTION_CHAMPIONS].delete_many({"summary": SYNTHETIC_NOTE})
    log.info(
        "wiped synthetic data: genomes=%d evals=%d generations=%d champions=%d",
        g.deleted_count, f.deleted_count, gn.deleted_count, c.deleted_count,
    )


def _diversity(genomes: list[Genome], rng: random.Random, sample_pairs: int = 30) -> float:
    if len(genomes) < 2:
        return 0.0
    pairs = []
    for _ in range(min(sample_pairs, len(genomes) * (len(genomes) - 1) // 2)):
        a, b = rng.sample(genomes, 2)
        pairs.append(gene_distance(a, b))
    return round(statistics.mean(pairs), 3) if pairs else 0.0


async def main(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    rng = random.Random(args.seed)

    db = await get_db()

    if args.replace:
        await _wipe_synthetic(db)

    query_ids = await _fetch_query_ids(db)
    log.info("using %d queries for evaluations", len(query_ids))

    now = datetime.now(timezone.utc)
    all_genomes_by_gen: dict[int, list[Genome]] = {}
    fitness_eval_docs: list[dict] = []
    generation_docs: list[dict] = []

    # ------ Gen 0: random population ------
    gen0 = random_population(POP_SIZE, generation=0, rng=rng)
    for g in gen0:
        g.notes = SYNTHETIC_NOTE
    all_genomes_by_gen[0] = gen0

    for gen in range(1, N_GENERATIONS):
        prev = all_genomes_by_gen[gen - 1]
        # Each gen has POP_SIZE fresh-uuid offspring derived from prev gen via
        # crossover + mutate. We don't carry elite ids forward — that would
        # duplicate _ids in the genomes collection. Lineage is preserved via
        # parent_ids on every offspring.
        children: list[Genome] = []
        for _ in range(POP_SIZE):
            p1, p2 = rng.sample(prev, 2)
            child = uniform_crossover(p1, p2, rng=rng, generation=gen)
            child = mutate(child, rate=MUTATION_RATE, rng=rng)
            child.notes = SYNTHETIC_NOTE
            children.append(child)

        all_genomes_by_gen[gen] = children

    # ------ Generate fitness_evaluations + generation summary docs ------
    for gen, pop in all_genomes_by_gen.items():
        lo, hi = GEN_FITNESS_RANGES[gen]
        # Re-roll fitness for this generation snapshot
        for g in pop:
            composite = round(rng.uniform(lo, hi), 3)
            g.fitness = FitnessSummary(
                composite=composite,
                n_evaluations=QUERIES_PER_GEN,
                last_updated=now - timedelta(minutes=(N_GENERATIONS - gen) * 8),
            )

        # 5 fitness_evaluations per genome
        for g in pop:
            for q_idx, qid in enumerate(query_ids[:QUERIES_PER_GEN]):
                composite = max(0.0, min(1.0, g.fitness.composite + rng.uniform(-0.08, 0.08)))
                eval_doc = FitnessEvaluation(
                    genome_id=g.id,
                    query_id=qid,
                    generation=gen,
                    run_id=SYNTHETIC_NOTE,
                    generated_answer=f"Synthetic answer for genome {g.id[:8]} on query {q_idx}.",
                    retrieval_trace=_trace(rng),
                    coordination_trace={"protocol": g.coordination_genes.protocol, "synthetic": True},
                    components=_components(composite, rng),
                    composite_fitness=round(composite, 3),
                    judge_critique=f"Synthetic critique. Genome scored {round(composite, 3)} for relevance + accuracy.",
                    timestamp=now - timedelta(minutes=(N_GENERATIONS - gen) * 8 + (QUERIES_PER_GEN - q_idx)),
                )
                fitness_eval_docs.append(eval_doc.model_dump(by_alias=True))

        # Generation summary doc
        composites = [g.fitness.composite for g in pop]
        elite_ids = [g.id for g in sorted(pop, key=lambda g: -g.fitness.composite)[:ELITE_K]]
        generation_docs.append({
            "generation": gen,
            "population_size": POP_SIZE,
            "best_fitness": round(max(composites), 3),
            "mean_fitness": round(statistics.mean(composites), 3),
            "diversity_index": _diversity(pop, rng),
            "selection": "synthetic",
            "crossover_rate": 1.0,
            "mutation_rate": MUTATION_RATE,
            "elite_genome_ids": elite_ids,
            "created_at": now - timedelta(minutes=(N_GENERATIONS - gen) * 8),
        })

    # ------ Genome status: latest gen alive, prior gens retired ------
    latest_gen = N_GENERATIONS - 1
    genome_docs: list[dict] = []
    for gen, pop in all_genomes_by_gen.items():
        for g in pop:
            g.status = "alive" if gen == latest_gen else "retired"
            genome_docs.append(g.model_dump(by_alias=True))

    log.info(
        "prepared %d genomes, %d evals, %d generation summaries",
        len(genome_docs), len(fitness_eval_docs), len(generation_docs),
    )

    # ------ Insert ------
    if genome_docs:
        await db[COLLECTION_GENOMES].insert_many(genome_docs)
    if fitness_eval_docs:
        await db[COLLECTION_FITNESS_EVALUATIONS].insert_many(fitness_eval_docs)
    if generation_docs:
        await db[COLLECTION_GENERATIONS].insert_many(generation_docs)

    # ------ Champions: top 2 from latest generation ------
    latest_pop = all_genomes_by_gen[latest_gen]
    top_two = sorted(latest_pop, key=lambda g: -g.fitness.composite)[:2]
    champion_docs = []
    for g in top_two:
        champ = Champion(
            genome_id=g.id,
            promoted_at_generation=latest_gen,
            composite_fitness=g.fitness.composite,
            summary=SYNTHETIC_NOTE,
        )
        champion_docs.append(champ.model_dump(by_alias=True))
    if champion_docs:
        await db[COLLECTION_CHAMPIONS].insert_many(champion_docs)

    log.info("inserted: %d genomes, %d evals, %d generations, %d champions",
             len(genome_docs), len(fitness_eval_docs), len(generation_docs), len(champion_docs))

    # Sanity report
    counts = {
        "genomes(alive)": await db[COLLECTION_GENOMES].count_documents({"status": "alive"}),
        "genomes(retired)": await db[COLLECTION_GENOMES].count_documents({"status": "retired"}),
        "fitness_evaluations": await db[COLLECTION_FITNESS_EVALUATIONS].count_documents({"run_id": SYNTHETIC_NOTE}),
        "generations(synthetic)": await db[COLLECTION_GENERATIONS].count_documents({"selection": "synthetic"}),
        "champions(synthetic)": await db[COLLECTION_CHAMPIONS].count_documents({"summary": SYNTHETIC_NOTE}),
    }
    log.info("post-seed counts: %s", counts)

    await close_client()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed synthetic Darwin evolution data.")
    parser.add_argument("--replace", action="store_true", help="Wipe synthetic data before seeding.")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility.")
    return parser.parse_args()


def _resolve_uri_into_env() -> None:
    if os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI"):
        return
    try:
        uri = subprocess.check_output(
            ["gcloud", "secrets", "versions", "access", "latest",
             "--secret=darwin-mongodb-uri", "--project=grantx-fleet"],
            text=True,
        ).strip()
        os.environ["MONGODB_URI"] = uri
    except Exception as exc:
        log.warning("could not resolve MONGODB_URI from gcloud: %s", exc)


if __name__ == "__main__":
    _resolve_uri_into_env()
    asyncio.run(main(parse_args()))
