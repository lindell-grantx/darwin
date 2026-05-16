"""Pass 3 PR-2: two-stage multi-axis Nash (top-K full + tail averaged)."""

from darwin.evolution.nash_msne import PayoffMatrix
from darwin.evolution.nash_two_stage import (
    DEFAULT_TOP_K,
    DEFAULT_TOP_M,
    DEFAULT_TOP_Q,
    solve_two_stage_nash,
)


def test_defaults_documented():
    assert DEFAULT_TOP_K == 10
    assert DEFAULT_TOP_M == 10
    assert DEFAULT_TOP_Q == 5


def test_small_payoff_uses_top_stage_only():
    """When population fits in top-K, no tail to combine."""
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
    strategy = solve_two_stage_nash(pm)
    assert len(strategy) == 3
    assert abs(sum(strategy.values()) - 1.0) < 1e-6
    assert all(0.30 <= w <= 0.40 for w in strategy.values())


def test_large_payoff_partitions_top_and_tail():
    """With more than top-K defenders, the bottom defenders get tail weights."""
    defender_ids = [f"d{i}" for i in range(15)]
    pm = PayoffMatrix(
        defender_ids=defender_ids,
        attacker_ids=["a1"],
        query_classes=["q1"],
        scores={
            (f"d{i}", "a1", "q1"): (0.9 if i < 10 else 0.1)
            for i in range(15)
        },
    )
    strategy = solve_two_stage_nash(pm)
    assert len(strategy) == 15
    assert abs(sum(strategy.values()) - 1.0) < 1e-6
    top_mass = sum(strategy[f"d{i}"] for i in range(10))
    assert top_mass > 0.9


def test_renormalization_invariant():
    """Output weights always sum to 1.0."""
    pm = PayoffMatrix(
        defender_ids=[f"d{i}" for i in range(20)],
        attacker_ids=[f"a{i}" for i in range(20)],
        query_classes=[f"q{i}" for i in range(8)],
        scores={
            (f"d{i}", f"a{j}", f"q{k}"): 0.5
            for i in range(20) for j in range(20) for k in range(8)
        },
    )
    strategy = solve_two_stage_nash(pm)
    assert abs(sum(strategy.values()) - 1.0) < 1e-6


def test_empty_payoff_returns_empty():
    pm = PayoffMatrix(defender_ids=[], attacker_ids=[], query_classes=[], scores={})
    assert solve_two_stage_nash(pm) == {}
