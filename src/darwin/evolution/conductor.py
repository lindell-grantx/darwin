"""Evolution conductor: change-stream consumer + generation rollover.

This module ties the evolution loop together. The intended deployment is one
long-running asyncio task (`watch_evaluations`) that subscribes to the
fitness_evaluations change-stream and triggers `evolve_generation` once
EVALS_PER_GEN_THRESHOLD inserts have landed for a given generation.

Polling fallback: if change streams aren't available, set `use_polling=True`
when calling `watch_evaluations` and it will poll the count every 1 s.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from darwin.db.client import watch_collection
from darwin.db.schemas import (
    COLLECTION_FITNESS_EVALUATIONS,
    COLLECTION_GENERATIONS,
    COLLECTION_GENOMES,
    COLLECTION_NASH_STRATEGIES,
    Genome,
    NashStrategy,
)
from darwin.db.schemas import COLLECTION_EVOLUTION_EVENTS
from darwin.evolution.nash_msne import PayoffMatrix, solve_two_axis_nash
from darwin.evolution.nash_two_stage import solve_two_stage_nash
from darwin.evolution import (
    ELITE_K,
    EVALS_PER_GEN_THRESHOLD,
    MUTATION_RATE,
    N_PARENTS,
    POP_SIZE,
)
from darwin.evolution.population import (
    birth_offspring,
    promote_to_champion,
    retire_genomes,
)
from darwin.evolution.selection import (
    aggregate_mean_fitness_by_generation,
    elite_select,
    tournament_select,
)
from darwin.evolution.dgm_select import (
    count_children_per_genome,
    dgm_weighted_select,
)
from darwin.evolution.novelty import novelty_reject
from darwin.evolution.islands import migrate, should_migrate
from darwin.evolution.lipizzaner import assign_to_grid
from darwin.evolution.plateau import should_use_opus
from darwin.genome.mutate import mutate
from darwin.genome.types import gene_distance
from darwin.attacker.evolution import attacker_evolve_generation


log = logging.getLogger(__name__)


__all__ = [
    "evolve_generation",
    "gen_already_evolved",
    "watch_evaluations",
]


_DIVERSITY_PAIR_CAP = 50


async def gen_already_evolved(db: AsyncIOMotorDatabase, generation: int) -> bool:
    """Has generation `generation+1` already been written to the `generations` collection?

    Used as the idempotency check before evolving — a single change-stream
    burst might trigger multiple consumers in race; this prevents double-rolls.
    """

    doc = await db[COLLECTION_GENERATIONS].find_one(
        {"generation": generation + 1},
        projection={"_id": 1},
    )
    return doc is not None


def _diversity_index(genomes: list[Genome], rng: random.Random) -> float:
    """Mean pairwise gene_distance over up to `_DIVERSITY_PAIR_CAP` distinct pairs."""

    n = len(genomes)
    if n < 2:
        return 0.0

    all_pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    if len(all_pairs) > _DIVERSITY_PAIR_CAP:
        sample = rng.sample(all_pairs, _DIVERSITY_PAIR_CAP)
    else:
        sample = all_pairs

    total = 0.0
    for i, j in sample:
        total += gene_distance(genomes[i], genomes[j])
    return total / len(sample)


async def evolve_generation(
    db: AsyncIOMotorDatabase,
    generation: int,
    *,
    rng: Optional[random.Random] = None,
) -> int:
    """Roll generation N → N+1. Returns the new generation number.

    See ARCHITECTURE.md §4 for the full pseudocode.
    """

    if rng is None:
        rng = random.Random()

    if await gen_already_evolved(db, generation):
        log.info("already evolved gen %d", generation)
        return generation + 1

    fitness_by_id = await aggregate_mean_fitness_by_generation(db, generation)

    cursor = db[COLLECTION_GENOMES].find(
        {"status": {"$in": ["alive", "champion"]}, "generation": generation}
    )
    raw_docs = await cursor.to_list(length=None)
    genomes: list[Genome] = []
    for doc in raw_docs:
        g = Genome.model_validate(doc)
        g.fitness.composite = float(fitness_by_id.get(g.id, 0.0))
        genomes.append(g)

    if not genomes:
        log.warning(
            "[evolve] gen %d has no alive/champion genomes; skipping", generation
        )
        return generation + 1

    elites = elite_select(genomes, ELITE_K)
    elite_ids = {e.id for e in elites}

    n_children_map = await count_children_per_genome(db)
    parents = dgm_weighted_select(
        genomes,
        N_PARENTS,
        n_children_map=n_children_map,
        rng=rng,
    )

    fitness_history = await _load_fitness_history(db, last_n_gens=10)
    use_opus = should_use_opus(generation, fitness_history)
    if use_opus:
        log.info(
            "Opus mutation pass active for gen %d (plateau or cadence trigger)",
            generation + 1,
        )

    offspring_n = max(0, POP_SIZE - len(elites))
    offspring = await birth_offspring(
        db,
        parents,
        offspring_n,
        generation + 1,
        mutation_rate=MUTATION_RATE,
        rng=rng,
        use_reflective=True,
        use_opus=use_opus,
    )

    # Apply novelty rejection — re-mutate any child too similar to recent archive
    recent_archive = (offspring + elites)[-50:]
    filtered_offspring = []
    for child in offspring:
        if novelty_reject(child, recent_archive, threshold=0.95):
            child = mutate(child, rate=0.5, rng=rng)
        filtered_offspring.append(child)
    offspring = filtered_offspring

    # Run migration on schedule, then persist island_id changes back to Mongo —
    # without this write, migrate() mutates in-memory island_id values that
    # the next generation never sees.
    if should_migrate(generation + 1):
        migration_pool = offspring + list(elites)
        migrate(migration_pool, rng=rng)
        for g in migration_pool:
            await db[COLLECTION_GENOMES].update_one(
                {"_id": g.id},
                {"$set": {"island_id": g.island_id}},
            )

    # Pass 2: assign grid positions to new offspring + elites
    assign_to_grid(offspring + list(elites))
    # Persist grid_position back to Mongo
    for g in offspring + list(elites):
        if g.grid_position is not None:
            await db[COLLECTION_GENOMES].update_one(
                {"_id": g.id},
                {"$set": {"grid_position": list(g.grid_position)}},
            )

    # Pass 2: every K=2 generations, evolve attackers as well
    ATTACKER_EVOLVE_INTERVAL = 2
    if (generation + 1) % ATTACKER_EVOLVE_INTERVAL == 0:
        await attacker_evolve_generation(db, n_offspring=5, generation=generation)

    # Pass 2: every 10 generations, recompute two-axis Nash MSNE strategy
    NASH_RECOMPUTE_INTERVAL = 10
    if (generation + 1) % NASH_RECOMPUTE_INTERVAL == 0:
        await _recompute_two_axis_nash(db, generation=generation + 1)

    if elite_ids:
        await db[COLLECTION_GENOMES].update_many(
            {"_id": {"$in": list(elite_ids)}},
            {"$set": {"generation": generation + 1, "status": "alive"}},
        )

    to_retire = [g.id for g in genomes if g.id not in elite_ids]
    if to_retire:
        await retire_genomes(db, to_retire)

    fitness_values = [g.fitness.composite for g in genomes]
    best_fitness = max(fitness_values) if fitness_values else 0.0
    mean_fitness = (
        sum(fitness_values) / len(fitness_values) if fitness_values else 0.0
    )

    diversity_pool = list(offspring) + list(elites)
    diversity = _diversity_index(diversity_pool, rng)

    await db[COLLECTION_GENERATIONS].insert_one(
        {
            "generation": generation + 1,
            "population_size": POP_SIZE,
            "best_fitness": float(best_fitness),
            "mean_fitness": float(mean_fitness),
            "diversity_index": float(diversity),
            "selection": "tournament+elite",
            "crossover_rate": 1.0,
            "mutation_rate": MUTATION_RATE,
            "elite_genome_ids": [e.id for e in elites],
            "created_at": datetime.now(timezone.utc),
        }
    )

    # Mirror into the bridge collection so Hono's change stream can pick it up
    # (time-series collections don't support `watch()`).
    try:
        await db[COLLECTION_EVOLUTION_EVENTS].insert_one(
            {
                "event_type": "generation.evolved",
                "generation": generation + 1,
                "payload": {
                    "best_fitness": float(best_fitness),
                    "mean_fitness": float(mean_fitness),
                    "diversity_index": float(diversity),
                    "n_offspring": len(offspring),
                    "n_elites": len(elites),
                    "elite_genome_ids": [e.id for e in elites],
                },
                "created_at": datetime.now(timezone.utc),
            }
        )
    except Exception as exc:
        log.warning("evolution_events publish failed for gen %d: %s", generation + 1, exc)

    if elites:
        try:
            top = elites[0]
            await promote_to_champion(db, top, top.fitness.composite)
        except Exception as exc:
            log.warning("champion promotion failed for %s: %s", elites[0].id, exc)

    log.info(
        "[evolve] gen %d → %d best=%.4f mean=%.4f diversity=%.4f elites=%d offspring=%d",
        generation,
        generation + 1,
        best_fitness,
        mean_fitness,
        diversity,
        len(elites),
        len(offspring),
    )

    return generation + 1


async def _maybe_evolve_for_gen(
    db: AsyncIOMotorDatabase,
    gen: int,
    rng: Optional[random.Random],
) -> None:
    count = await db[COLLECTION_FITNESS_EVALUATIONS].count_documents(
        {"generation": gen}
    )
    if count < EVALS_PER_GEN_THRESHOLD:
        return
    if await gen_already_evolved(db, gen):
        return
    await evolve_generation(db, gen, rng=rng)


async def _watch_change_stream(
    db: AsyncIOMotorDatabase,
    rng: Optional[random.Random],
) -> None:
    async for change in watch_collection(
        db[COLLECTION_FITNESS_EVALUATIONS],
        operation_types=("insert",),
    ):
        try:
            full = change.get("fullDocument") or {}
            gen = full.get("generation")
            if gen is None:
                continue
            await _maybe_evolve_for_gen(db, int(gen), rng)
        except Exception as exc:
            log.exception("watch loop iteration failed: %s", exc)


async def _poll_loop(
    db: AsyncIOMotorDatabase,
    poll_interval_sec: float,
    rng: Optional[random.Random],
) -> None:
    while True:
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": "$generation",
                        "n": {"$sum": 1},
                    }
                },
                {"$match": {"n": {"$gte": EVALS_PER_GEN_THRESHOLD}}},
                {"$sort": {"_id": 1}},
            ]
            evolved_cursor = db[COLLECTION_GENERATIONS].find(
                {}, projection={"generation": 1, "_id": 0}
            )
            evolved_docs = await evolved_cursor.to_list(length=None)
            evolved_gens = {int(d["generation"]) for d in evolved_docs}

            agg_cursor = db[COLLECTION_FITNESS_EVALUATIONS].aggregate(pipeline)
            target: Optional[int] = None
            async for row in agg_cursor:
                gen_n = int(row["_id"])
                # gen_already_evolved checks for gen+1 in generations
                if (gen_n + 1) not in evolved_gens:
                    target = gen_n
                    break

            if target is not None:
                await evolve_generation(db, target, rng=rng)
        except Exception as exc:
            log.exception("polling loop iteration failed: %s", exc)

        await asyncio.sleep(poll_interval_sec)


async def watch_evaluations(
    db: AsyncIOMotorDatabase,
    *,
    use_polling: bool = False,
    poll_interval_sec: float = 1.0,
    rng: Optional[random.Random] = None,
) -> None:
    """Long-running consumer that triggers evolve_generation when threshold met.

    Two modes:
    - **Change-stream (default)**: subscribe to fitness_evaluations inserts.
    - **Polling (fallback)**: every `poll_interval_sec`, find the lowest
      generation with ≥ EVALS_PER_GEN_THRESHOLD evals that hasn't been
      evolved; evolve it.

    Runs forever. The caller wraps in asyncio.create_task and cancels on
    shutdown. Catches per-iteration exceptions and logs them; never raises.
    """

    if use_polling:
        await _poll_loop(db, poll_interval_sec, rng)
        return

    try:
        await _watch_change_stream(db, rng)
    except Exception as exc:
        log.exception("change-stream watcher failed, exiting: %s", exc)


async def _load_fitness_history(db, *, last_n_gens: int = 10) -> list[float]:
    """Load best-fitness-per-generation for the last N generations."""
    cursor = (
        db[COLLECTION_GENERATIONS]
        .find({}, projection={"generation": 1, "best_fitness": 1, "_id": 0})
        .sort("generation", -1)
        .limit(last_n_gens)
    )
    docs = await cursor.to_list(length=last_n_gens)
    docs.reverse()
    return [float(d.get("best_fitness", 0.0)) for d in docs]


async def _recompute_two_axis_nash(db, *, generation: int) -> None:
    """Build a PayoffMatrix from recent fitness_evaluations + solve MSNE."""
    diff_map: dict[str, str] = {}
    async for q in db["queries"].find({}, projection={"_id": 1, "domain_tags": 1}):
        diff_map[str(q["_id"])] = ",".join(q.get("domain_tags") or [])

    cursor = db[COLLECTION_FITNESS_EVALUATIONS].find(
        {"generation": {"$gte": max(0, generation - 5)}},
        projection={"genome_id": 1, "attacker_id": 1, "query_id": 1, "composite_fitness": 1},
    )

    defender_ids: set[str] = set()
    attacker_ids: set[str] = set()
    query_classes: set[str] = set()
    sums: dict[tuple[str, str, str], float] = {}
    counts: dict[tuple[str, str, str], int] = {}

    async for row in cursor:
        d = row["genome_id"]
        a = row.get("attacker_id") or "_NONE_"
        q = diff_map.get(row["query_id"])
        if not q:
            continue
        defender_ids.add(d)
        attacker_ids.add(a)
        query_classes.add(q)
        key = (d, a, q)
        sums[key] = sums.get(key, 0.0) + float(row["composite_fitness"])
        counts[key] = counts.get(key, 0) + 1

    averaged = {k: sums[k] / counts[k] for k in sums}
    pm = PayoffMatrix(
        defender_ids=sorted(defender_ids),
        attacker_ids=sorted(attacker_ids),
        query_classes=sorted(query_classes),
        scores=averaged,
    )
    strategy = solve_two_stage_nash(pm)
    if strategy:
        ns = NashStrategy(
            weights=strategy,
            snapshot_generation=generation,
        )
        await db[COLLECTION_NASH_STRATEGIES].insert_one(
            ns.model_dump(by_alias=True, mode="json")
        )
        log.info("two-axis Nash recomputed: %d defenders weighted at gen %d", len(strategy), generation)
