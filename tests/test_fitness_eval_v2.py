"""v2 MVP: FitnessEvaluation gains an `attacker_id` axis."""

from darwin.db.schemas import FitnessComponents, FitnessEvaluation


def _components() -> FitnessComponents:
    return FitnessComponents(
        relevance=0.7,
        accuracy=0.7,
        coverage=0.7,
        latency_ms=1000,
        cost_usd=0.01,
    )


def test_attacker_id_field_default_is_none():
    """attacker_id is nullable so existing v1 evals remain valid."""
    e = FitnessEvaluation(
        genome_id="genome-x",
        query_id="query-y",
        generation=0,
        run_id="run-1",
        generated_answer="answer",
        components=_components(),
        composite_fitness=0.7,
    )
    assert e.attacker_id is None


def test_attacker_id_can_be_set():
    e = FitnessEvaluation(
        genome_id="genome-x",
        query_id="query-y",
        generation=0,
        run_id="run-1",
        generated_answer="answer",
        components=_components(),
        composite_fitness=0.4,
        attacker_id="attacker-z",
    )
    assert e.attacker_id == "attacker-z"
