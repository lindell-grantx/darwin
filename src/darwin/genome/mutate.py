"""Per-gene mutation operators."""

from __future__ import annotations

import random
from typing import Optional

from darwin.db.schemas import Genome


__all__ = ["mutate"]


def mutate(
    g: Genome,
    rate: float,
    *,
    rng: Optional[random.Random] = None,
) -> Genome:
    """Return a new Genome with each field independently mutated at probability `rate`.

    Operators (per field type):
    - bounded float: gaussian step `value + rng.gauss(0, 0.1)`, clamped to range
    - categorical/enum/Literal: replace with a uniformly-random different value
    - bounded int: ±1 step (or jump to a random in-range value with 25% prob)
    - list (source_routing): swap one tag in/out, keep non-empty

    The returned genome:
    - has the same id, generation, status, parent_ids as `g` (only gene fields change)
    - resets fitness summary to defaults (mutation invalidates prior eval)
    - rate=0 returns an exact copy (model-validate roundtrip is fine)
    """

    raise NotImplementedError("B2: implement mutate (gaussian for floats, swap for enums)")
