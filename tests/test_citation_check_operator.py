"""Pass 3 PR-4: citation_check operator (post-gen hallucination flag)."""

from darwin.retrieval.operators.citation_check import (
    build_citation_check_prompt,
    parse_citation_check_response,
)


def test_build_prompt_includes_answer_and_chunks():
    chunks = [{"text": "fact A"}, {"text": "fact B"}]
    prompt = build_citation_check_prompt("The answer cites fact A.", chunks)
    assert "fact A" in prompt
    assert "fact B" in prompt
    assert "answer cites fact A" in prompt


def test_parse_citation_check_response_passed_true():
    response = '{"passed": true, "issues": []}'
    parsed = parse_citation_check_response(response)
    assert parsed["passed"] is True
    assert parsed["issues"] == []


def test_parse_citation_check_response_with_issues():
    response = '{"passed": false, "issues": ["claim about X has no source"]}'
    parsed = parse_citation_check_response(response)
    assert parsed["passed"] is False
    assert len(parsed["issues"]) == 1


def test_parse_citation_check_response_invalid_returns_default():
    """Invalid response → assume passed=True (avoid false positives blocking flow)."""
    parsed = parse_citation_check_response("not json")
    assert parsed["passed"] is True
    parsed = parse_citation_check_response('{"missing_passed": false}')
    assert parsed["passed"] is True
