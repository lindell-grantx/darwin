"""Pass 1: FitnessEvaluation gains process-reward fields."""

from darwin.db.schemas import FitnessEvaluation


def _minimal_fields():
    # FitnessComponents requires all 5 sub-fields; spec's 2-key shorthand
    # cannot validate. Provide a complete components doc.
    return dict(
        run_id="run-x",
        genome_id="genome-y",
        query_id="query-z",
        generation=0,
        composite_fitness=0.5,
        generated_answer="hello",
        components={
            "relevance": 0.5,
            "accuracy": 0.5,
            "coverage": 0.5,
            "latency_ms": 1000,
            "cost_usd": 0.0,
        },
    )


def test_tool_call_count_default_is_zero():
    e = FitnessEvaluation(**_minimal_fields())
    assert e.tool_call_count == 0


def test_tool_call_count_can_be_set():
    e = FitnessEvaluation(**_minimal_fields(), tool_call_count=5)
    assert e.tool_call_count == 5


def test_step_coherence_default_is_none():
    e = FitnessEvaluation(**_minimal_fields())
    assert e.step_coherence is None


def test_step_coherence_can_be_float():
    e = FitnessEvaluation(**_minimal_fields(), step_coherence=0.8)
    assert e.step_coherence == 0.8


def test_process_latency_ms_default_is_none():
    e = FitnessEvaluation(**_minimal_fields())
    assert e.process_latency_ms is None


def test_process_latency_ms_can_be_int():
    e = FitnessEvaluation(**_minimal_fields(), process_latency_ms=1240)
    assert e.process_latency_ms == 1240
