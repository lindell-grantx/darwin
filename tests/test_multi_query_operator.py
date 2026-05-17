"""Pass 3 PR-4: multi_query operator tests (pure functions; integration mocked)."""

from darwin.retrieval.operators.multi_query import (
    MAX_VARIANTS,
    build_multi_query_prompt,
    parse_variants_response,
)


def test_max_variants_capped_at_5():
    assert MAX_VARIANTS == 5


def test_build_prompt_includes_query_and_max_variants():
    prompt = build_multi_query_prompt("how do I create a vector index?")
    assert "how do I create a vector index?" in prompt
    assert "5" in prompt


def test_parse_variants_returns_list():
    response = '{"variants": ["query a", "query b", "query c"]}'
    parsed = parse_variants_response(response, original="orig")
    assert parsed == ["orig", "query a", "query b", "query c"]


def test_parse_variants_caps_at_max():
    response = '{"variants": ["v1", "v2", "v3", "v4", "v5", "v6", "v7"]}'
    parsed = parse_variants_response(response, original="orig")
    assert len(parsed) <= MAX_VARIANTS + 1


def test_parse_variants_returns_original_on_invalid():
    assert parse_variants_response("not json", original="o") == ["o"]
    assert parse_variants_response('{"missing": "variants"}', original="o") == ["o"]
