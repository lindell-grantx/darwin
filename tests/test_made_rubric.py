"""Pass 1: MADE rubric returns a vector of 5+ predicates per eval."""

from darwin.fitness.made_rubric import (
    MADE_PREDICATES,
    composite_from_predicates,
    decompose_judge_output,
)


def test_made_predicates_at_least_five():
    assert len(MADE_PREDICATES) >= 5
    assert "relevance" in MADE_PREDICATES
    assert "accuracy" in MADE_PREDICATES
    assert "groundedness" in MADE_PREDICATES


def test_decompose_judge_output_returns_vector():
    judge_out = {
        "relevance": 0.8,
        "accuracy": 0.7,
        "coverage": 0.6,
        "groundedness": 0.9,
        "rationale": "looks good",
    }
    vec = decompose_judge_output(judge_out)
    assert isinstance(vec, dict)
    assert all(p in vec for p in MADE_PREDICATES)
    assert all(0.0 <= vec[p] <= 1.0 for p in MADE_PREDICATES)


def test_composite_from_predicates_uniform_weight():
    vec = {p: 0.5 for p in MADE_PREDICATES}
    composite = composite_from_predicates(vec)
    assert abs(composite - 0.5) < 1e-9


def test_composite_from_predicates_handles_missing_keys():
    partial = {"relevance": 1.0}
    composite = composite_from_predicates(partial)
    expected = (1.0 + 0.5 * (len(MADE_PREDICATES) - 1)) / len(MADE_PREDICATES)
    assert abs(composite - expected) < 1e-9
