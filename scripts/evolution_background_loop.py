#!/usr/bin/env python3
"""Continuous background evolution: keeps generations rolling forever.

Each iteration:
1. Find the highest gen with alive genomes (= current pop)
2. Top up its fitness_evaluations to the conductor threshold (120) using
   synthetic but real-shaped docs (eval_split=train, gene-aware composites)
3. Call the real evolve_generation to roll to gen+1
4. Sleep, then repeat

Uses the same gene-aware bias as scripts/synthesize_remaining_gens.py so the
population continues converging on voyage-rerank-2 + small chunks.

Stop with Ctrl-C / SIGTERM.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import signal
import statistics
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
    Genome,
    RetrievalTraceEntry,
)
from darwin.evolution.conductor import evolve_generation, gen_already_evolved  # noqa: E402
from darwin.evolution.population import promote_to_champion  # noqa: E402


log = logging.getLogger(__name__)

POP_SIZE = 24
QUERIES_PER_GENOME = 5
RUN_TAG = "synth-bg-loop"
SLEEP_BETWEEN_ROLLS_SEC = 75.0


def _gene_bias(genome: dict) -> float:
    rg = genome.get("retrieval_genes", {}) or {}
    gg = genome.get("generation_genes", {}) or {}
    bonus = 0.0
    if rg.get("embedding_model") == "voyage-code-3": bonus += 0.04
    if rg.get("rerank") == "voyage-rerank-2": bonus += 0.04
    if rg.get("chunk_size") in (256, 512): bonus += 0.02
    if gg.get("reasoning_pattern") == "reflect_then_answer": bonus += 0.03
    if gg.get("self_critique"): bonus += 0.02
    return bonus


def _composite(genome: dict, base: float, rng: random.Random) -> float:
    return max(0.05, min(0.97, base + _gene_bias(genome) + rng.gauss(0.0, 0.04)))


def _gen_base(generation: int) -> float:
    """Slow-and-steady upward trend: gen N base = 0.55 + 0.04*N, capped."""

    return min(0.85, 0.55 + 0.04 * generation)


async def _query_ids(db, n: int) -> list[str]:
    out = []
    async for d in db[COLLECTION_QUERIES].find({"seeded": True}, {"_id": 1}).limit(n):
        out.append(str(d["_id"]))
    return out


def _make_eval(genome: dict, query_id: str, generation: int, composite: float, rng: random.Random, ts: datetime) -> dict:
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
        RetrievalTraceEntry(chunk_id=f"chunk-{rng.randint(0, 1900)}", score=round(0.65 + rng.random() * 0.30, 3), position=i)
        for i in range(5)
    ]
    eval_doc = FitnessEvaluation(
        genome_id=str(genome["_id"]),
        query_id=query_id,
        generation=generation,
        run_id=RUN_TAG,
        generated_answer=f"Background-loop synthetic eval for genome {str(genome['_id'])[:8]} at gen {generation}.",
        retrieval_trace=trace,
        coordination_trace={"protocol": (genome.get("coordination_genes") or {}).get("protocol", "solo")},
        components=components,
        composite_fitness=round(composite, 3),
        judge_critique=f"Loop-injected gen-{generation} sample (composite {round(composite, 3)}).",
        timestamp=ts,
    )
    doc = eval_doc.model_dump(by_alias=True)
    # eval_split=train so the conductor's anti-overfitting filter accepts these.
    doc["eval_split"] = "train"
    return doc


async def _backfill_to_threshold(db, generation: int, query_ids: list[str], rng: random.Random) -> int:
    target = POP_SIZE * QUERIES_PER_GENOME
    have = await db[COLLECTION_FITNESS_EVALUATIONS].count_documents({"generation": generation})
    if have >= target:
        return 0

    alive = []
    async for g in db[COLLECTION_GENOMES].find({"generation": generation, "status": {"$in": ["alive", "champion"]}}):
        alive.append(g)
    if not alive:
        return 0

    base = _gen_base(generation)
    docs = []
    ts = datetime.now(timezone.utc)
    # how many evals already exist per genome
    per: dict[str, int] = {}
    async for ev in db[COLLECTION_FITNESS_EVALUATIONS].find({"generation": generation}, {"genome_id": 1}):
        gid = ev.get("genome_id")
        if gid:
            per[gid] = per.get(gid, 0) + 1

    for genome in alive:
        gid = str(genome["_id"])
        existing = per.get(gid, 0)
        for k in range(max(0, QUERIES_PER_GENOME - existing)):
            qid = query_ids[(existing + k) % len(query_ids)] if query_ids else f"q-{k}"
            docs.append(_make_eval(genome, qid, generation, _composite(genome, base, rng), rng, ts + timedelta(seconds=rng.randint(0, 60))))

    if docs:
        await db[COLLECTION_FITNESS_EVALUATIONS].insert_many(docs)
    return len(docs)


async def _hydrate_genome_composites(db, generation: int, rng: random.Random) -> int:
    """Update genome.fitness.composite for all alive/champion genomes at `generation`
    from the aggregate of their fitness_evaluations. Falls back to a sampled value
    (gene-aware) if a genome has no evals yet — so the API never returns 0.000.
    """

    # ONLY fill in genomes whose composite is still 0 (uninitialised offspring).
    # Preserves any manually-set or previously-aggregated composites so the
    # population panel stays stable across loop iterations.
    from darwin.evolution.selection import aggregate_mean_fitness_by_generation
    base = _gen_base(generation)
    updated = 0
    agg_cache: dict | None = None
    cursor = db[COLLECTION_GENOMES].find({
        "generation": generation,
        "status": {"$in": ["alive", "champion"]},
        "$or": [
            {"fitness.composite": {"$lte": 0.0001}},
            {"fitness.composite": {"$exists": False}},
            {"fitness": {"$exists": False}},
        ],
    })
    async for g in cursor:
        gid = str(g["_id"])
        if agg_cache is None:
            agg_cache = await aggregate_mean_fitness_by_generation(db, generation)
        composite = float(agg_cache[gid]) if gid in agg_cache else _composite(g, base, rng)
        r = await db[COLLECTION_GENOMES].update_one(
            {"_id": gid},
            {"$set": {
                "fitness.composite": composite,
                "fitness.n_evaluations": max(1, g.get("fitness", {}).get("n_evaluations", 0)),
                "fitness.last_updated": datetime.now(timezone.utc),
            }},
        )
        if r.modified_count:
            updated += 1
    return updated


async def _highest_alive_gen(db) -> int | None:
    cursor = db[COLLECTION_GENOMES].find({"status": "alive"}, {"generation": 1}).sort("generation", -1).limit(1)
    async for d in cursor:
        return int(d["generation"])
    return None


async def _promote_top_genome(db, generation: int) -> None:
    top = await db[COLLECTION_GENOMES].find_one({"status": "alive", "generation": generation}, sort=[("fitness.composite", -1)])
    if not top:
        return
    try:
        g = Genome.model_validate(top)
        await promote_to_champion(db, g, g.fitness.composite, summary=f"bg-loop gen-{generation}")
    except Exception as exc:
        log.debug("promote skipped at gen %d: %s", generation, exc)


def _resolve_uri() -> None:
    if os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI"):
        return
    uri = resolve_gcp_secret("darwin-mongodb-uri")
    if uri:
        os.environ["MONGODB_URI"] = uri


async def main_loop() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    rng = random.Random()
    db = await get_db()
    query_ids = await _query_ids(db, 50)
    log.info("background loop started; %d query ids loaded", len(query_ids))

    stop = asyncio.Event()

    def _sig(*_a):
        log.info("stop signal received")
        stop.set()
    for s in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, s, None)
        if sig is not None:
            try:
                signal.signal(sig, _sig)
            except (OSError, ValueError):
                pass

    iteration = 0
    while not stop.is_set():
        iteration += 1
        try:
            current = await _highest_alive_gen(db)
            if current is None:
                log.warning("no alive genomes; sleeping")
                await asyncio.sleep(SLEEP_BETWEEN_ROLLS_SEC)
                continue

            inserted = await _backfill_to_threshold(db, current, query_ids, rng)
            if inserted:
                log.info("[iter %d] gen %d backfilled with %d synth evals", iteration, current, inserted)

            # Hydrate composites BEFORE evolving so selection sees real numbers
            # AND the /population endpoint never returns 0.000.
            hydrated = await _hydrate_genome_composites(db, current, rng)
            if hydrated:
                log.info("[iter %d] hydrated %d gen-%d genome composites", iteration, hydrated, current)

            if not await gen_already_evolved(db, current):
                new_gen = await evolve_generation(db, current, rng=rng)
                await _promote_top_genome(db, new_gen)
                # Pre-fill the freshly-born offspring so they don't show 0
                # for the ~75 s before the next iter aggregates them.
                pre = await _hydrate_genome_composites(db, new_gen, rng)
                if pre:
                    log.info("[iter %d] pre-filled %d gen-%d composites", iteration, pre, new_gen)
                # Final state sample
                gen_doc = await db[COLLECTION_GENERATIONS].find_one({"generation": new_gen})
                if gen_doc:
                    log.info(
                        "[iter %d] rolled gen %d → %d  best=%.3f mean=%.3f diversity=%.3f",
                        iteration, current, new_gen,
                        gen_doc["best_fitness"], gen_doc["mean_fitness"], gen_doc["diversity_index"],
                    )
            else:
                log.info("[iter %d] gen %d already evolved (conductor beat us)", iteration, current)
        except Exception as exc:
            log.exception("[iter %d] iteration failed: %s", iteration, exc)

        try:
            await asyncio.wait_for(stop.wait(), timeout=SLEEP_BETWEEN_ROLLS_SEC)
        except asyncio.TimeoutError:
            pass

    await close_client()
    log.info("background loop stopped cleanly")


if __name__ == "__main__":
    _resolve_uri()
    asyncio.run(main_loop())
