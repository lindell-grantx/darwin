"""Ancestor walker for the family-tree UI panel."""

from __future__ import annotations

from collections import deque
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from darwin.db.schemas import COLLECTION_GENOMES, Genome
from darwin.genome.types import gene_diff


__all__ = ["walk_ancestors"]


async def walk_ancestors(
    db: AsyncIOMotorDatabase,
    genome_id: str,
    *,
    max_depth: int = 10,
) -> list[dict[str, Any]]:
    """Walk `parent_ids` recursively up to `max_depth` levels.

    Returns a flat list of records:
        [{"genome": <Genome>, "depth": 1, "gene_diff": {...}}, ...]

    `gene_diff` compares each ancestor with its child (using
    `darwin.genome.types.gene_diff`). Cycle-safe (track visited ids). Returns
    [] if `genome_id` doesn't exist.
    """

    genomes = db[COLLECTION_GENOMES]
    root_doc = await genomes.find_one({"_id": genome_id})
    if root_doc is None:
        return []
    root = Genome.model_validate(root_doc)

    results: list[dict[str, Any]] = []
    visited: set[str] = {root.id}

    # Queue holds (child_genome, parent_id_to_visit, depth_of_parent).
    queue: deque[tuple[Genome, str, int]] = deque()
    for pid in root.parent_ids:
        queue.append((root, pid, 1))

    while queue:
        child, parent_id, depth = queue.popleft()
        if depth > max_depth:
            continue
        if parent_id in visited:
            continue
        visited.add(parent_id)

        ancestor_doc = await genomes.find_one({"_id": parent_id})
        if ancestor_doc is None:
            continue
        ancestor = Genome.model_validate(ancestor_doc)

        diff = gene_diff(ancestor, child)
        results.append({"genome": ancestor, "depth": depth, "gene_diff": diff})

        if depth < max_depth:
            for pid in ancestor.parent_ids:
                if pid not in visited:
                    queue.append((ancestor, pid, depth + 1))

    return results
