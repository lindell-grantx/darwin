"""Uniform crossover between two parent genomes."""

from __future__ import annotations

import random
from typing import Optional

from darwin.db.schemas import Genome


__all__ = ["uniform_crossover"]


def uniform_crossover(
    p1: Genome,
    p2: Genome,
    *,
    rng: Optional[random.Random] = None,
    generation: int,
) -> Genome:
    """Per-field uniform crossover.

    For every field across all three gene layers, pick the value from p1 or p2
    with 50/50 probability (independently per field — uniform crossover, not
    single-point). The child:
    - has `parent_ids = [p1.id, p2.id]`
    - has `generation = generation` (the destination generation)
    - has fresh `id`, `status="alive"`, fresh `fitness` summary
    - inherits no fitness data from parents

    Special handling for `source_routing` (a list): pick each tag from p1 with
    50% probability (union semantics); ensure the result is non-empty (fallback
    to p1's full list).
    """

    raise NotImplementedError("B2: implement uniform_crossover")
