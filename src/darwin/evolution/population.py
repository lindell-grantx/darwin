"""Population-level operations: birthing offspring, retiring genomes, promoting champions."""

from __future__ import annotations

import random
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from darwin.db.schemas import Champion, Genome


__all__ = [
    "birth_offspring",
    "promote_to_champion",
    "retire_genomes",
]


async def birth_offspring(
    db: AsyncIOMotorDatabase,
    parents: list[Genome],
    n: int,
    generation: int,
    *,
    mutation_rate: float,
    rng: Optional[random.Random] = None,
) -> list[Genome]:
    """Produce `n` offspring by repeated crossover+mutate from the parent pool.

    For each child:
    1. Pick two distinct parents at random (with replacement across iterations).
    2. `child = uniform_crossover(p1, p2, generation=generation)` (genome.crossover).
    3. `child = mutate(child, mutation_rate)` (genome.mutate).
    4. Insert into `genomes` collection.

    Returns the inserted Genome list (with assigned ids). Uses
    `db['genomes'].insert_many` for the bulk write.
    """

    raise NotImplementedError("B4: implement birth_offspring (calls crossover+mutate, bulk insert)")


async def retire_genomes(
    db: AsyncIOMotorDatabase,
    genome_ids: list[str],
) -> int:
    """Mark the listed genomes as `status="retired"`. Returns count modified.

    Uses `update_many({_id: {$in: genome_ids}}, {$set: {status: "retired"}})`.
    """

    raise NotImplementedError("B4: implement retire_genomes")


async def promote_to_champion(
    db: AsyncIOMotorDatabase,
    genome: Genome,
    peak_fitness: float,
    *,
    summary: Optional[str] = None,
) -> Champion:
    """Insert a Champion doc and flip the genome's status to "champion".

    Idempotent on (genome_id): if a champion already exists for this genome,
    update its peak_fitness if the new value is higher; otherwise no-op.
    """

    raise NotImplementedError("B4: implement promote_to_champion (idempotent insert + status flip)")
