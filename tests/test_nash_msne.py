"""Pass 2 PR-4: two-axis Nash MSNE solver tests."""

import pytest

from darwin.evolution.nash_msne import (
    PayoffMatrix,
    solve_two_axis_nash,
)


def test_solve_uniform_payoff_yields_uniform_strategy():
    pm = PayoffMatrix(
        defender_ids=["d1", "d2", "d3"],
        attacker_ids=["a1", "a2"],
        query_classes=["q1"],
        scores={
            ("d1", "a1", "q1"): 0.5, ("d1", "a2", "q1"): 0.5,
            ("d2", "a1", "q1"): 0.5, ("d2", "a2", "q1"): 0.5,
            ("d3", "a1", "q1"): 0.5, ("d3", "a2", "q1"): 0.5,
        },
    )
    strategy = solve_two_axis_nash(pm)
    weights = list(strategy.values())
    assert len(strategy) == 3
    assert abs(sum(weights) - 1.0) < 1e-6
    assert all(0.30 <= w <= 0.40 for w in weights)


def test_solve_dominant_defender_gets_high_weight():
    pm = PayoffMatrix(
        defender_ids=["dom", "weak"],
        attacker_ids=["a1", "a2"],
        query_classes=["q1"],
        scores={
            ("dom", "a1", "q1"): 0.9, ("dom", "a2", "q1"): 0.9,
            ("weak", "a1", "q1"): 0.1, ("weak", "a2", "q1"): 0.1,
        },
    )
    strategy = solve_two_axis_nash(pm)
    assert strategy["dom"] > 0.9
    assert strategy["weak"] < 0.1


def test_solve_empty_payoff_returns_empty():
    pm = PayoffMatrix(defender_ids=[], attacker_ids=[], query_classes=[], scores={})
    strategy = solve_two_axis_nash(pm)
    assert strategy == {}
