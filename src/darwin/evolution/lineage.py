"""Ancestor walker for the family-tree UI panel."""

from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from darwin.db.schemas import Genome


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

    raise NotImplementedError("B4: implement walk_ancestors (BFS, cycle-safe)")
