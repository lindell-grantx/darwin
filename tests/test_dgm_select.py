"""Pass 1: DGM weighted parent sampling tests."""

import random


class _FakeGenome:
    def __init__(self, gid: str, fitness: float):
        self.id = gid
        from darwin.db.schemas import FitnessSummary
        self.fitness = FitnessSummary(composite=fitness)


def test_dgm_weighted_select_higher_fitness_more_likely():
    from darwin.evolution.dgm_select import dgm_weighted_select

    high = _FakeGenome("h", 0.9)
    low = _FakeGenome("l", 0.1)
    n_children = {"h": 0, "l": 0}

    rng = random.Random(0)
    samples = []
    for _ in range(1000):
        result = dgm_weighted_select(
            [high, low], n_parents=1, n_children_map=n_children, rng=rng,
        )
        samples.append(result[0].id)

    high_count = samples.count("h")
    assert high_count > 800


def test_dgm_weighted_select_penalizes_overexplored_lineages():
    from darwin.evolution.dgm_select import dgm_weighted_select

    a = _FakeGenome("a", 0.7)
    b = _FakeGenome("b", 0.7)
    n_children = {"a": 0, "b": 50}

    rng = random.Random(0)
    samples = []
    for _ in range(1000):
        result = dgm_weighted_select(
            [a, b], n_parents=1, n_children_map=n_children, rng=rng,
        )
        samples.append(result[0].id)

    a_count = samples.count("a")
    assert a_count > 900


def test_dgm_returns_correct_count():
    from darwin.evolution.dgm_select import dgm_weighted_select

    pool = [_FakeGenome(f"g{i}", 0.5) for i in range(10)]
    n_children = {g.id: 0 for g in pool}

    rng = random.Random(0)
    result = dgm_weighted_select(
        pool, n_parents=5, n_children_map=n_children, rng=rng,
    )
    assert len(result) == 5
