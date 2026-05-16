"""Pass 2 PR-4: MAP-Elites defender archive + DNS fallback."""

from darwin.evolution.map_elites import (
    BC_DIMS,
    behavior_descriptor,
    map_elites_admit,
    dns_score,
)


def test_bc_dims_three():
    assert len(BC_DIMS) == 3
    assert "retrieval_strategy_class" in BC_DIMS


def test_behavior_descriptor_returns_three_tuple():
    import random
    from darwin.genome.factory import random_genome
    g = random_genome(rng=random.Random(0))
    bc = behavior_descriptor(g)
    assert isinstance(bc, tuple)
    assert len(bc) == 3


def test_map_elites_admit_replaces_lower_fitness():
    cells: dict[tuple, dict] = {}
    cells[("a", "b", "c")] = {"id": "old", "composite_fitness": 0.4}
    admitted = map_elites_admit(
        cells, ("a", "b", "c"), {"id": "new", "composite_fitness": 0.7},
    )
    assert admitted is True
    assert cells[("a", "b", "c")]["id"] == "new"


def test_map_elites_admit_keeps_higher_fitness():
    cells: dict[tuple, dict] = {"k": {"id": "old", "composite_fitness": 0.7}}
    admitted = map_elites_admit(
        cells, "k", {"id": "new", "composite_fitness": 0.4},
    )
    assert admitted is False


def test_dns_score_subtracts_density_penalty():
    base = 0.7
    score = dns_score(base, neighborhood_density=5)
    assert score < base
    score_alone = dns_score(base, neighborhood_density=0)
    assert score_alone > score
