"""Pass 2: Lipizzaner toroidal spatial grid for two-population co-evolution.

Defenders and attackers occupy positions on a GRID_SIZE x GRID_SIZE toroidal grid.
Each defender at position (r, c) is evaluated against attackers in its 3x3
neighborhood (with wraparound). This creates locality that prevents either
population from globally homogenizing.

Reference: Lipizzaner (https://github.com/ALFA-group/lipizzaner-gan).
For Pass 2 we ship 3x3 (9 cells per population). Pass 3 can scale to 5x5.
"""

from __future__ import annotations

from typing import Iterable


GRID_SIZE: int = 3


def toroidal_offset(pos: tuple[int, int], offset: tuple[int, int]) -> tuple[int, int]:
    """Apply a 2D offset to a grid position, wrapping at GRID_SIZE."""
    r = (pos[0] + offset[0]) % GRID_SIZE
    c = (pos[1] + offset[1]) % GRID_SIZE
    return (r, c)


def neighborhood(pos: tuple[int, int]) -> list[tuple[int, int]]:
    """Return the 3x3 toroidal neighborhood centered at pos (includes self)."""
    out = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            out.append(toroidal_offset(pos, (dr, dc)))
    return out


def assign_to_grid(population: list) -> None:
    """In-place: assign grid_position round-robin across population.

    For population larger than GRID_SIZE^2, multiple residents share each cell.
    """
    n_cells = GRID_SIZE * GRID_SIZE
    for i, member in enumerate(population):
        cell_idx = i % n_cells
        member.grid_position = (cell_idx // GRID_SIZE, cell_idx % GRID_SIZE)
