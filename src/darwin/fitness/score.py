"""Composite fitness scoring."""

from __future__ import annotations

DEFAULT_WEIGHTS = {"relevance": 0.4, "accuracy": 0.4, "coverage": 0.2}


def composite_fitness(
    components: dict[str, float],
    weights: dict[str, float] | None = None,
) -> float:
    """Weighted sum of relevance, accuracy, and coverage clamped to [0, 1]."""
    active_weights = weights or DEFAULT_WEIGHTS
    value = sum(float(components.get(name, 0.0)) * weight for name, weight in active_weights.items())
    return max(0.0, min(1.0, round(value, 4)))
