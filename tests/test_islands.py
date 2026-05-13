"""Pass 1: island model + migration tests."""

import random


def _make_genome(gid: str, fitness: float, island_id: int):
    from darwin.genome.factory import random_genome
    g = random_genome(rng=random.Random(hash(gid) % 1000))
    g.fitness.composite = fitness
    g.island_id = island_id
    g.__dict__["id"] = gid  # hack since auto-generated
    return g


def test_assign_to_islands_round_robin():
    from darwin.evolution.islands import assign_to_islands

    population = [_make_genome(f"g{i}", 0.5, 0) for i in range(10)]
    assign_to_islands(population, n_islands=3)
    counts = {i: 0 for i in range(3)}
    for g in population:
        counts[g.island_id] += 1
    assert all(2 <= c <= 4 for c in counts.values())
    assert sum(counts.values()) == 10


def test_migrate_swaps_best_per_island():
    from darwin.evolution.islands import migrate, group_by_island

    rng = random.Random(0)
    pop = [
        _make_genome("a", 0.9, 0),
        _make_genome("b", 0.5, 0),
        _make_genome("c", 0.8, 1),
        _make_genome("d", 0.3, 1),
    ]
    migrate(pop, rng=rng)
    a = next(g for g in pop if g.id == "a")
    c = next(g for g in pop if g.id == "c")
    # Best of each island (a, c) should now be in a different island
    assert a.island_id != 0 or c.island_id != 1


def test_migrate_no_op_with_one_island():
    from darwin.evolution.islands import migrate

    pop = [_make_genome("a", 0.9, 0), _make_genome("b", 0.5, 0)]
    rng = random.Random(0)
    migrate(pop, rng=rng)
    assert all(g.island_id == 0 for g in pop)
