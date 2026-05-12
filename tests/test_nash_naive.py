"""v2 MVP: naive uniform Nash strategy."""

import pytest

from darwin.evolution.nash_naive import build_uniform_strategy


def test_uniform_strategy_three_defenders():
    s = build_uniform_strategy(["d1", "d2", "d3"])
    assert s.weights == {"d1": 1/3, "d2": 1/3, "d3": 1/3}
    assert abs(sum(s.weights.values()) - 1.0) < 1e-9


def test_uniform_strategy_dedupes():
    s = build_uniform_strategy(["d1", "d1", "d2"])
    assert s.weights == {"d1": 0.5, "d2": 0.5}


def test_uniform_strategy_empty_raises():
    with pytest.raises(ValueError):
        build_uniform_strategy([])


def test_strategy_carries_snapshot_generation():
    s = build_uniform_strategy(["d1", "d2"], snapshot_generation=7)
    assert s.snapshot_generation == 7
