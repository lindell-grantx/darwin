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
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from darwin.evolution import (
    ELITE_K,
    EVALS_PER_GEN_THRESHOLD,
    MUTATION_RATE,
    N_PARENTS,
    POP_SIZE,
)


log = logging.getLogger(__name__)


__all__ = [
    "evolve_generation",
    "gen_already_evolved",
    "watch_evaluations",
]


async def gen_already_evolved(db: AsyncIOMotorDatabase, generation: int) -> bool:
    """Has generation `generation+1` already been written to the `generations` collection?

    Used as the idempotency check before evolving — a single change-stream
    burst might trigger multiple consumers in race; this prevents double-rolls.
    """

    raise NotImplementedError("B5: implement gen_already_evolved")


async def evolve_generation(
    db: AsyncIOMotorDatabase,
    generation: int,
    *,
    rng: Optional[random.Random] = None,
) -> int:
    """Roll generation N → N+1. Returns the new generation number.

    Steps (per ARCHITECTURE.md §4):
    1. Aggregate mean fitness per genome (selection.aggregate_mean_fitness_by_generation)
    2. Hydrate the alive Genome objects from the genomes collection, attach mean fitness
    3. Pick elites (selection.elite_select) and parents (selection.tournament_select)
    4. Birth POP_SIZE - ELITE_K offspring (population.birth_offspring) at generation+1
    5. Promote elites to generation+1 (update_many status stays "alive", generation = N+1)
    6. Retire all other gen-N genomes (population.retire_genomes)
    7. Insert a doc into `generations` (time-series): {generation: N+1, population_size,
       best_fitness, mean_fitness, diversity_index, selection: "tournament+elite",
       crossover_rate: 1.0, mutation_rate: MUTATION_RATE, elite_genome_ids}
    8. (Optional) Promote the top-1 genome by peak fitness as a champion
    9. Returns N+1.

    Re-entrancy: call `gen_already_evolved(db, generation)` first; if true,
    log and return generation+1 unchanged.
    """

    raise NotImplementedError("B5: implement evolve_generation (orchestrate selection+population)")


async def watch_evaluations(
    db: AsyncIOMotorDatabase,
    *,
    use_polling: bool = False,
    poll_interval_sec: float = 1.0,
    rng: Optional[random.Random] = None,
) -> None:
    """Long-running consumer that triggers evolve_generation when threshold met.

    Two modes:
    - **Change-stream (default)**: `db.fitness_evaluations.watch([{$match:{operationType:"insert"}}])`
      Each insert event: read `fullDocument.generation`, count
      `fitness_evaluations` for that gen; if ≥ EVALS_PER_GEN_THRESHOLD AND
      not gen_already_evolved → evolve_generation.
    - **Polling (fallback)**: every `poll_interval_sec`, find the lowest
      generation with ≥ EVALS_PER_GEN_THRESHOLD evals that hasn't been
      evolved; evolve it.

    Runs forever. The caller wraps in asyncio.create_task and cancels on
    shutdown. Catches per-iteration exceptions and logs them; never raises.
    """

    raise NotImplementedError("B5: implement watch_evaluations (change-stream + polling fallback)")
