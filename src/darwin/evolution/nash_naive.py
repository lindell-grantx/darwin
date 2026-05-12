"""v2 MVP: naive uniform Nash strategy.

Pass 2 replaces this with a real two-axis COvolve MSNE solver. For MVP we
just sample uniformly from the Pareto-front top-3, which gives mixed-strategy
behavior at inference without the matrix solving overhead.
"""

from __future__ import annotations

from darwin.db.schemas import NashStrategy


def build_uniform_strategy(
    defender_ids: list[str],
    *,
    snapshot_generation: int = 0,
) -> NashStrategy:
    """Return a NashStrategy with uniform weights over the unique defender ids.

    Empty list raises ValueError.
    Duplicates are deduped (input ordering preserved via dict-insertion order).
    """
    if not defender_ids:
        raise ValueError("Cannot build a Nash strategy over zero defenders")

    unique: dict[str, None] = {}
    for d in defender_ids:
        unique.setdefault(d, None)

    n = len(unique)
    weight = 1.0 / n
    return NashStrategy(
        weights={d: weight for d in unique},
        snapshot_generation=snapshot_generation,
    )
