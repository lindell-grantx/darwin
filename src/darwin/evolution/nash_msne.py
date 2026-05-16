"""Pass 2: two-axis Nash MSNE solver — defenders robust across attacker portfolio
AND query-type portfolio.

For Pass 2 we use a simplified LP formulation via nashpy. We average payoffs
across the query axis to reduce to a 2-player matrix game (defender row,
attacker column), then solve for the row-player's mixed-strategy equilibrium.

Reference: COvolve (arXiv:2603.28386).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np


log = logging.getLogger(__name__)


@dataclass
class PayoffMatrix:
    defender_ids: list[str]
    attacker_ids: list[str]
    query_classes: list[str]
    scores: dict[tuple[str, str, str], float]


def solve_two_axis_nash(pm: PayoffMatrix) -> dict[str, float]:
    """Solve for defender mixed strategy that maximizes worst-case payoff.

    Returns dict[defender_id -> weight in [0, 1], summing to 1]. Empty input -> empty dict.
    """
    if not pm.defender_ids or not pm.attacker_ids:
        return {}

    n_d = len(pm.defender_ids)
    n_a = len(pm.attacker_ids)

    # Average across the query axis
    matrix = np.zeros((n_d, n_a))
    counts = np.zeros((n_d, n_a))
    for (d, a, q), score in pm.scores.items():
        try:
            i = pm.defender_ids.index(d)
            j = pm.attacker_ids.index(a)
        except ValueError:
            continue
        matrix[i, j] += score
        counts[i, j] += 1
    counts[counts == 0] = 1.0
    matrix = matrix / counts

    # Two-player zero-sum from defender's perspective: defender max, attacker min.
    weights: list[float] | None = None
    try:
        import warnings

        import nashpy as nash
        game = nash.Game(matrix, -matrix)

        eqs: list = []
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # support_enumeration handles degenerate / dominated games where
            # vertex_enumeration returns nothing.
            try:
                eqs = list(game.support_enumeration())
            except Exception as exc:
                log.warning("support_enumeration failed: %s", exc)
            if not eqs:
                try:
                    eqs = list(game.vertex_enumeration())
                except Exception as exc:
                    log.warning("vertex_enumeration failed: %s", exc)

        # Filter out any equilibria with non-finite entries.
        clean_eqs = []
        for row, col in eqs:
            row_arr = np.asarray(row, dtype=float)
            col_arr = np.asarray(col, dtype=float)
            if (
                row_arr.shape == (n_d,)
                and col_arr.shape == (n_a,)
                and np.all(np.isfinite(row_arr))
                and np.all(np.isfinite(col_arr))
            ):
                clean_eqs.append((row_arr, col_arr))

        if not clean_eqs:
            log.warning("no usable Nash equilibrium found — falling back to uniform")
        else:
            # Group equilibria by value; when many tie at the best value (degenerate
            # game, e.g. uniform payoffs), average their row strategies so we don't
            # arbitrarily pick a pure-strategy corner.
            scored = []
            for row_arr, col_arr in clean_eqs:
                value = float(row_arr @ matrix @ col_arr)
                scored.append((value, row_arr))
            best_value = max(v for v, _ in scored)
            best_rows = [r for v, r in scored if v >= best_value - 1e-9]
            avg_row = np.mean(np.stack(best_rows, axis=0), axis=0)
            weights = [float(x) for x in avg_row]
    except Exception as exc:
        log.warning("nashpy solve failed (%s) — falling back to uniform", exc)

    if weights is None:
        weights = [1.0 / n_d] * n_d

    weights = [max(0.0, float(w)) for w in weights]
    total = sum(weights)
    if total <= 0:
        weights = [1.0 / n_d] * n_d
    else:
        weights = [w / total for w in weights]

    return dict(zip(pm.defender_ids, weights))
