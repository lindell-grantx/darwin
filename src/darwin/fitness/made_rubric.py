"""MADE rubric: decompose judge output into N verifiable predicates.

Vector-valued fitness signals enable Pareto-front and lexicase selection downstream.
The 5 predicates extend the existing 4-dim judge with confidence_calibration
(does the answer's hedging match its actual groundedness?).

Reference: MADE (arXiv:2511.19489) — decomposing vague rubrics into specific
verifiable sub-requirements improved DevAI satisfaction from 39.9% to 61.9%.

Pass 2 will add tool_call_efficiency + step_coherence as separate predicates
(currently captured at the FitnessEvaluation level, not as judge predicates).
"""

from __future__ import annotations


MADE_PREDICATES: tuple[str, ...] = (
    "relevance",
    "accuracy",
    "coverage",
    "groundedness",
    "confidence_calibration",
)


def decompose_judge_output(judge_out: dict) -> dict[str, float]:
    """Convert raw judge output into a normalized predicate vector.

    Missing keys → 0.5 (neutral). Out-of-range values clamped to [0, 1].
    Pulls confidence_calibration from judge if present, else estimates as
    1 - |relevance - groundedness| (proxy: a well-calibrated answer's
    apparent quality should match its actual groundedness).
    """
    vec: dict[str, float] = {}
    for p in MADE_PREDICATES:
        if p in judge_out:
            vec[p] = max(0.0, min(1.0, float(judge_out[p])))
        elif p == "confidence_calibration":
            relevance = float(judge_out.get("relevance", 0.5))
            groundedness = float(judge_out.get("groundedness", 0.5))
            vec[p] = 1.0 - abs(relevance - groundedness)
        else:
            vec[p] = 0.5
    return vec


def composite_from_predicates(
    vec: dict[str, float],
    weights: dict[str, float] | None = None,
) -> float:
    """Weighted mean of predicate vector. Missing predicates default to 0.5."""
    weights = weights or {p: 1.0 for p in MADE_PREDICATES}
    total_weight = sum(weights.values())
    score = 0.0
    for p in MADE_PREDICATES:
        v = vec.get(p, 0.5)
        w = weights.get(p, 0.0)
        score += w * v
    return score / total_weight if total_weight > 0 else 0.0
