"""Pass 3: two-stage multi-axis Nash MSNE.

Top-K defenders x top-M attackers x top-Q query classes get true multi-axis MSNE
(matrix shape K x (M*Q), tractable for K=10/M=10/Q=5 -> 10x50). Tail defenders
fall back to averaged-payoff Nash. Combined and renormalized using each stage's
Nash game value as a weight so the higher-payoff stage dominates.

When the input fits entirely in the top-K (no tail), result matches a direct
multi-axis solve.

Reference: COvolve (arXiv:2603.28386).
"""

from __future__ import annotations

import logging
import warnings
from collections import defaultdict

import numpy as np

from darwin.evolution.nash_msne import PayoffMatrix, solve_two_axis_nash


log = logging.getLogger(__name__)


DEFAULT_TOP_K: int = 10
DEFAULT_TOP_M: int = 10
DEFAULT_TOP_Q: int = 5


def _rank_defenders(pm: PayoffMatrix) -> list[str]:
    means: dict[str, list[float]] = defaultdict(list)
    for (d, _a, _q), score in pm.scores.items():
        means[d].append(score)
    return sorted(
        pm.defender_ids,
        key=lambda d: -sum(means.get(d, [0.0])) / max(1, len(means.get(d, [0.0]))),
    )


def _rank_attackers(pm: PayoffMatrix) -> list[str]:
    means: dict[str, list[float]] = defaultdict(list)
    for (_d, a, _q), score in pm.scores.items():
        means[a].append(score)
    return sorted(
        pm.attacker_ids,
        key=lambda a: sum(means.get(a, [1.0])) / max(1, len(means.get(a, [1.0]))),
    )


def _rank_query_classes(pm: PayoffMatrix) -> list[str]:
    counts: dict[str, int] = defaultdict(int)
    for (_d, _a, q), _score in pm.scores.items():
        counts[q] += 1
    return sorted(pm.query_classes, key=lambda q: -counts.get(q, 0))


def _solve_multi_axis_msne(
    defender_ids: list[str],
    attacker_ids: list[str],
    query_classes: list[str],
    scores: dict[tuple[str, str, str], float],
) -> tuple[dict[str, float], float]:
    """True multi-axis MSNE on (n_d, n_a * n_q) matrix.

    Returns (strategy, game_value). game_value is the defender's minimax payoff
    under the Nash equilibrium (used by the caller to weight top vs tail).
    """
    n_d = len(defender_ids)
    cols = [(a, q) for a in attacker_ids for q in query_classes]
    n_c = len(cols)

    if n_d == 0 or n_c == 0:
        return {}, 0.0

    matrix = np.zeros((n_d, n_c))
    for i, d in enumerate(defender_ids):
        for j, (a, q) in enumerate(cols):
            matrix[i, j] = scores.get((d, a, q), 0.5)

    weights: list[float] | None = None
    game_value: float = float(matrix.mean())

    try:
        import nashpy as nash

        game = nash.Game(matrix, -matrix)
        candidate_rows: list[np.ndarray] = []
        candidate_values: list[float] = []

        # Small matrices: support_enumeration finds all equilibria (handles
        # degenerate games gracefully). Large matrices: skip it (exponential
        # blowup on uniform-payoff games) and use Lemke-Howson with multiple
        # pivots instead.
        use_support_enum = n_d * n_c <= 64

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if use_support_enum:
                try:
                    for row, col in game.support_enumeration():
                        row_arr = np.asarray(row, dtype=float)
                        col_arr = np.asarray(col, dtype=float)
                        if row_arr.shape != (n_d,) or col_arr.shape != (n_c,):
                            continue
                        if not (np.all(np.isfinite(row_arr)) and np.all(np.isfinite(col_arr))):
                            continue
                        value = float(row_arr @ matrix @ col_arr)
                        if not np.isfinite(value):
                            continue
                        candidate_rows.append(row_arr)
                        candidate_values.append(value)
                except Exception as exc:
                    log.warning("support_enumeration failed: %s", exc)

            if not candidate_rows:
                pivot_count = min(n_d + n_c, 16)
                for label in range(pivot_count):
                    try:
                        row, col = game.lemke_howson(initial_dropped_label=label)
                    except Exception:
                        continue
                    row_arr = np.asarray(row, dtype=float)
                    col_arr = np.asarray(col, dtype=float)
                    if row_arr.shape != (n_d,) or col_arr.shape != (n_c,):
                        continue
                    if not (np.all(np.isfinite(row_arr)) and np.all(np.isfinite(col_arr))):
                        continue
                    value = float(row_arr @ matrix @ col_arr)
                    if not np.isfinite(value):
                        continue
                    candidate_rows.append(row_arr)
                    candidate_values.append(value)

        if candidate_rows:
            best_value = max(candidate_values)
            best_rows = [
                r for r, v in zip(candidate_rows, candidate_values)
                if v >= best_value - 1e-9
            ]
            avg_row = np.mean(np.stack(best_rows, axis=0), axis=0)
            weights = [float(x) for x in avg_row]
            game_value = best_value
    except Exception as exc:
        log.warning("multi-axis MSNE failed (%s) - uniform fallback", exc)

    if weights is None:
        weights = [1.0 / n_d] * n_d

    weights = [max(0.0, float(w)) for w in weights]
    total = sum(weights)
    if total <= 0:
        weights = [1.0 / n_d] * n_d
    else:
        weights = [w / total for w in weights]

    return dict(zip(defender_ids, weights)), float(game_value)


def _stage_value(strategy: dict[str, float], scores: dict[tuple[str, str, str], float]) -> float:
    """Defender's average payoff under `strategy` over all (a, q) cells in scores."""
    if not strategy or not scores:
        return 0.0
    per_d_mean: dict[str, list[float]] = defaultdict(list)
    for (d, _a, _q), s in scores.items():
        per_d_mean[d].append(s)
    total = 0.0
    for d, w in strategy.items():
        vals = per_d_mean.get(d, [])
        if not vals:
            continue
        total += w * (sum(vals) / len(vals))
    return total


def solve_two_stage_nash(
    pm: PayoffMatrix,
    *,
    top_k: int = DEFAULT_TOP_K,
    top_m: int = DEFAULT_TOP_M,
    top_q: int = DEFAULT_TOP_Q,
) -> dict[str, float]:
    """Two-stage Nash: top-K defenders get true multi-axis; tail gets averaged.

    Top and tail are combined using each stage's defender game value as a
    sharpened weight, so the higher-payoff stage dominates the mixture. This is
    the policy choice from COvolve: the meta-strategy should put mass where
    the worst-case payoff is higher.
    """
    if not pm.defender_ids or not pm.attacker_ids:
        return {}

    ranked_defenders = _rank_defenders(pm)
    ranked_attackers = _rank_attackers(pm)[:top_m]
    ranked_queries = _rank_query_classes(pm)[:top_q]

    top_defenders = ranked_defenders[:top_k]
    tail_defenders = ranked_defenders[top_k:]

    top_set = set(top_defenders)
    tail_set = set(tail_defenders)
    attacker_set = set(ranked_attackers)
    query_set = set(ranked_queries)

    top_scores = {
        (d, a, q): s
        for (d, a, q), s in pm.scores.items()
        if d in top_set and a in attacker_set and q in query_set
    }
    top_strategy, top_value = _solve_multi_axis_msne(
        top_defenders, ranked_attackers, ranked_queries, top_scores,
    )

    if not tail_defenders:
        if not top_strategy:
            n = len(pm.defender_ids)
            return {d: 1.0 / n for d in pm.defender_ids}
        total = sum(top_strategy.values())
        if total <= 0:
            n = len(top_strategy)
            return {d: 1.0 / n for d in top_strategy}
        return {d: w / total for d, w in top_strategy.items()}

    tail_score_dict = {
        (d, a, q): s
        for (d, a, q), s in pm.scores.items()
        if d in tail_set
    }
    tail_pm = PayoffMatrix(
        defender_ids=tail_defenders,
        attacker_ids=ranked_attackers,
        query_classes=ranked_queries,
        scores=tail_score_dict,
    )
    tail_strategy = solve_two_axis_nash(tail_pm)
    tail_value = _stage_value(tail_strategy, tail_score_dict)

    # Weight stages by their Nash game value, sharpened so a clearly stronger
    # stage dominates. Temperature controls sharpness; small temperature -> hard
    # split, large -> softer mix.
    temperature: float = 0.05
    safe_top = max(top_value, 0.0)
    safe_tail = max(tail_value, 0.0)
    if safe_top == 0.0 and safe_tail == 0.0:
        top_share = len(top_defenders) / (len(top_defenders) + len(tail_defenders))
    else:
        exp_top = np.exp(safe_top / temperature)
        exp_tail = np.exp(safe_tail / temperature)
        denom = exp_top + exp_tail
        if not np.isfinite(denom) or denom <= 0:
            top_share = 1.0 if safe_top >= safe_tail else 0.0
        else:
            top_share = float(exp_top / denom)
    tail_share = 1.0 - top_share

    combined: dict[str, float] = {}
    for d, w in top_strategy.items():
        combined[d] = w * top_share
    for d, w in tail_strategy.items():
        combined[d] = combined.get(d, 0.0) + w * tail_share

    total = sum(combined.values())
    if total <= 0:
        n = len(pm.defender_ids)
        return {d: 1.0 / n for d in pm.defender_ids}
    return {d: w / total for d, w in combined.items()}
