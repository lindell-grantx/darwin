"""Pass 2 PR-3: Lipizzaner toroidal grid tests."""

from darwin.evolution.lipizzaner import (
    GRID_SIZE,
    assign_to_grid,
    neighborhood,
    toroidal_offset,
)


def test_grid_size_is_three():
    assert GRID_SIZE == 3


def test_toroidal_offset_wraps():
    assert toroidal_offset((0, 0), (-1, -1)) == (2, 2)
    assert toroidal_offset((2, 2), (1, 1)) == (0, 0)
    assert toroidal_offset((1, 1), (0, 0)) == (1, 1)


def test_neighborhood_returns_nine_cells():
    nbrs = neighborhood((1, 1))
    assert len(nbrs) == 9
    assert (1, 1) in nbrs
    assert (0, 0) in nbrs
    assert (2, 2) in nbrs


def test_neighborhood_wraps_at_corners():
    nbrs = neighborhood((0, 0))
    assert (2, 2) in nbrs
    assert (0, 1) in nbrs
    assert (1, 0) in nbrs


def test_assign_to_grid_distributes_round_robin():
    class _Stub:
        def __init__(self):
            self.grid_position = None

    pop = [_Stub() for _ in range(9)]
    assign_to_grid(pop)
    positions = {p.grid_position for p in pop}
    assert len(positions) == 9
