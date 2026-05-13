"""Island model — partition population into N islands; migrate best across periodically.

Cheapest diversity-preservation mechanism with the strongest empirical track record
(AlphaEvolve / OpenEvolve). Default: 3 islands, migrate every 5 generations.
"""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Sequence

from darwin.db.schemas import Genome


N_ISLANDS_DEFAULT: int = 3
MIGRATION_INTERVAL: int = 5


def assign_to_islands(population: list[Genome], n_islands: int = N_ISLANDS_DEFAULT) -> None:
    """In-place: assign island_id round-robin across population."""
    for i, g in enumerate(population):
        g.island_id = i % n_islands


def group_by_island(population: Sequence[Genome]) -> dict[int, list[Genome]]:
    """Return dict mapping island_id -> [genomes in that island]."""
    by_island: dict[int, list[Genome]] = defaultdict(list)
    for g in population:
        by_island[g.island_id].append(g)
    return dict(by_island)


def migrate(population: list[Genome], *, rng: random.Random) -> None:
    """In-place: move highest-fitness genome of each island to a random different island.

    No-op if population is partitioned into 0 or 1 islands.
    """
    by_island = group_by_island(population)
    if len(by_island) < 2:
        return

    island_ids = sorted(by_island.keys())
    for src_id in island_ids:
        residents = by_island[src_id]
        if not residents:
            continue
        best = max(residents, key=lambda g: g.fitness.composite)
        dst_options = [i for i in island_ids if i != src_id]
        dst_id = rng.choice(dst_options)
        best.island_id = dst_id


def should_migrate(generation: int) -> bool:
    """True every MIGRATION_INTERVAL generations starting at generation 1."""
    return generation > 0 and generation % MIGRATION_INTERVAL == 0
