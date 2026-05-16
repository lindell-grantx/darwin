"""Pass 2: attacker generation rollover — LLM mutation + QD admit + PAIRED regret fitness.

Reference: PAIRED (https://research.google/blog/paired/) — adversary fitness is the
gap between protagonist (evolved best) and antagonist (baseline). Avoids both
pathologies: attackers that are impossible (best loses to baseline → regret 0)
and trivial (best ties baseline → regret 0).
"""

from __future__ import annotations

import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

from darwin.attacker.llm_mutator import mutate_attacker
from darwin.attacker.qd_archive import cell_key_for_attacker_async, qd_admit
from darwin.db.schemas import (
    Attacker,
    AttackerArchive,
    COLLECTION_ATTACKER_ARCHIVE,
    COLLECTION_ATTACKERS,
)


log = logging.getLogger(__name__)


def paired_regret(*, best_defender_score: float, baseline_score: float) -> float:
    """PAIRED regret: max(0, best - baseline). Higher = more discriminating attack."""
    return max(0.0, best_defender_score - baseline_score)


async def attacker_evolve_generation(
    db: AsyncIOMotorDatabase,
    *,
    n_offspring: int,
    generation: int,
) -> int:
    """Roll attacker generation N -> N+1.

    1. Read all attackers
    2. Pick top-K parents by composite_fitness (default top-quartile)
    3. LLM-mutate each parent to produce n_offspring children
    4. QD-admit each child into the archive
    5. Persist new attackers + updated archive
    """
    cursor = db[COLLECTION_ATTACKERS].find({})
    raw = await cursor.to_list(length=None)
    if not raw:
        log.warning("no attackers seeded — cannot evolve")
        return generation
    attackers = [Attacker.model_validate(d) for d in raw]
    attackers.sort(key=lambda a: a.composite_fitness, reverse=True)
    parents = attackers[: max(1, len(attackers) // 4)]

    children: list[Attacker] = []
    for i in range(n_offspring):
        parent = parents[i % len(parents)]
        child = await mutate_attacker(parent)
        child.generation = generation + 1
        children.append(child)

    if children:
        await db[COLLECTION_ATTACKERS].insert_many(
            [c.model_dump(by_alias=True, mode="json") for c in children]
        )

    # Refresh QD archive from current attackers + children
    archive_cells: dict[tuple[str, str], dict] = {}
    for a in attackers + children:
        cell = await cell_key_for_attacker_async(a)
        candidate = {"id": a.id, "composite_fitness": a.composite_fitness}
        qd_admit(archive_cells, cell, candidate)

    # Persist updated archive (wipe + reinsert at Pass 2 scale)
    await db[COLLECTION_ATTACKER_ARCHIVE].delete_many({})
    for cell_key, entry in archive_cells.items():
        archive = AttackerArchive(cell_key=cell_key, attacker_ids=[entry["id"]])
        await db[COLLECTION_ATTACKER_ARCHIVE].insert_one(
            archive.model_dump(by_alias=True, mode="json")
        )

    log.info(
        "attacker gen %d -> %d: %d children, %d archive cells",
        generation, generation + 1, len(children), len(archive_cells),
    )
    return generation + 1
