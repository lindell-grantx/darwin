"""Population-level operations: birthing offspring, retiring genomes, promoting champions."""

from __future__ import annotations

import random
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from darwin.db.schemas import (
    COLLECTION_CHAMPIONS,
    COLLECTION_FITNESS_EVALUATIONS,
    COLLECTION_GENOMES,
    Champion,
    Genome,
)
from darwin.genome.crossover import uniform_crossover
from darwin.genome.mutate import mutate
from darwin.genome.reflective import reflect_and_mutate


__all__ = [
    "birth_offspring",
    "promote_to_champion",
    "retire_genomes",
]


OPUS_MODEL_ID = "claude-opus-4-7"


async def _reflective_or_mechanical(
    child: Genome,
    parents: list[Genome],
    db: AsyncIOMotorDatabase,
    *,
    mutation_rate: float,
    rng: random.Random,
    use_opus: bool = False,
) -> Genome:
    """Apply reflective mutation if a parent has trace data; else fall back to mechanical.

    `use_opus=True` routes the reflective LLM call to Opus 4.7 (plateau / cadence
    trigger from the conductor); otherwise the Vertex default is used.
    """
    primary_parent = max(parents, key=lambda g: g.fitness.composite)

    # Find the WORST clean (no-attacker) eval for this parent — that's the most
    # informative trace to reflect on (where the genome failed).
    trace_doc = await db[COLLECTION_FITNESS_EVALUATIONS].find_one(
        {"genome_id": primary_parent.id, "attacker_id": None},
        sort=[("composite_fitness", 1)],
    )
    if not trace_doc:
        return mutate(child, mutation_rate, rng=rng)

    trace = {
        "answer": trace_doc.get("generated_answer", ""),
        "chunks": (trace_doc.get("chunks") or [])[:3],  # top 3 to keep prompt short
    }
    judge = dict(trace_doc.get("components") or {})
    judge["rationale"] = trace_doc.get("rationale", "")

    model = OPUS_MODEL_ID if use_opus else None
    mutated, _meta = await reflect_and_mutate(child, trace, judge, rng=rng, model=model)
    return mutated


async def birth_offspring(
    db: AsyncIOMotorDatabase,
    parents: list[Genome],
    n: int,
    generation: int,
    *,
    mutation_rate: float,
    rng: Optional[random.Random] = None,
    use_reflective: bool = True,
    use_opus: bool = False,
) -> list[Genome]:
    """Produce `n` offspring by repeated crossover+mutate from the parent pool.

    For each child:
    1. Pick two distinct parents at random.
    2. child = uniform_crossover(p1, p2, generation=generation)
    3. If use_reflective and a trace exists: child = reflect_and_mutate(child, trace, judge)
       Else: child = mutate(child, mutation_rate)
    4. Insert into `genomes` collection via insert_many.

    `use_opus=True` upgrades the reflective LLM to Opus for this generation.
    """

    if n <= 0:
        return []
    if len(parents) < 2:
        raise ValueError("birth_offspring requires at least 2 parents")

    rng = rng or random.Random()

    children: list[Genome] = []
    for _ in range(n):
        p1, p2 = rng.sample(parents, 2)
        child = uniform_crossover(p1, p2, generation=generation, rng=rng)
        if use_reflective:
            child = await _reflective_or_mechanical(
                child,
                parents=[p1, p2],
                db=db,
                mutation_rate=mutation_rate,
                rng=rng,
                use_opus=use_opus,
            )
        else:
            child = mutate(child, mutation_rate, rng=rng)
        children.append(child)

    docs = [c.model_dump(by_alias=True) for c in children]
    await db[COLLECTION_GENOMES].insert_many(docs)
    return children


async def retire_genomes(
    db: AsyncIOMotorDatabase,
    genome_ids: list[str],
) -> int:
    """Mark the listed genomes as `status="retired"`. Returns count modified.

    Uses `update_many({_id: {$in: genome_ids}}, {$set: {status: "retired"}})`.
    """

    if not genome_ids:
        return 0
    result = await db[COLLECTION_GENOMES].update_many(
        {"_id": {"$in": list(genome_ids)}},
        {"$set": {"status": "retired"}},
    )
    return result.modified_count


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

    champions = db[COLLECTION_CHAMPIONS]
    existing = await champions.find_one({"genome_id": genome.id})

    if existing is not None:
        existing_peak = existing.get("composite_fitness", float("-inf"))
        if existing_peak >= peak_fitness:
            await db[COLLECTION_GENOMES].update_one(
                {"_id": genome.id},
                {"$set": {"status": "champion"}},
            )
            return Champion.model_validate(existing)

        update_doc: dict = {"composite_fitness": peak_fitness}
        if summary is not None:
            update_doc["summary"] = summary
        update_doc["promoted_at_generation"] = genome.generation
        await champions.update_one(
            {"_id": existing["_id"]},
            {"$set": update_doc},
        )
        await db[COLLECTION_GENOMES].update_one(
            {"_id": genome.id},
            {"$set": {"status": "champion"}},
        )
        refreshed = await champions.find_one({"_id": existing["_id"]})
        return Champion.model_validate(refreshed)

    champion = Champion(
        genome_id=genome.id,
        promoted_at_generation=genome.generation,
        composite_fitness=peak_fitness,
        summary=summary,
    )
    await champions.insert_one(champion.model_dump(by_alias=True))
    await db[COLLECTION_GENOMES].update_one(
        {"_id": genome.id},
        {"$set": {"status": "champion"}},
    )
    return champion
