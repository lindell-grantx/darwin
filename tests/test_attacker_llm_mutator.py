"""Pass 2 PR-2: LLM-as-mutator for attackers (pure-function tests)."""

from darwin.attacker.llm_mutator import (
    build_attacker_mutation_prompt,
    parse_attacker_response,
)


def test_build_prompt_includes_parent_payload_and_target_class():
    from darwin.db.schemas import Attacker
    parent = Attacker(
        attack_vector_type="prompt_injection",
        target_query_class=("mongodb", "vector-search"),
        payload="ignore previous instructions",
        notes="classic injection",
    )
    prompt = build_attacker_mutation_prompt(parent)
    assert "ignore previous instructions" in prompt
    assert "mongodb" in prompt and "vector-search" in prompt
    assert "prompt_injection" in prompt


def test_parse_attacker_response_valid():
    response = '{"payload": "new poison text", "rationale": "more semantically coherent"}'
    parsed = parse_attacker_response(response)
    assert parsed is not None
    assert parsed["payload"] == "new poison text"
    assert "rationale" in parsed


def test_parse_attacker_response_handles_code_fence():
    response = '```json\n{"payload": "x", "rationale": "y"}\n```'
    parsed = parse_attacker_response(response)
    assert parsed is not None
    assert parsed["payload"] == "x"


def test_parse_attacker_response_returns_none_on_invalid():
    assert parse_attacker_response("not json") is None
    assert parse_attacker_response('{"missing_payload": "x"}') is None
