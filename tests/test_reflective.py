"""Pass 1: GEPA-style reflective mutation tests (no LLM required for these)."""

import random

import pytest

from darwin.genome.reflective import (
    apply_edit,
    build_mutation_prompt,
    parse_edit_response,
)


def _stub_genome():
    from darwin.genome.factory import random_genome
    return random_genome(rng=random.Random(0))


def test_build_mutation_prompt_includes_genome_and_trace():
    g = _stub_genome()
    trace = {"answer": "wrong answer", "chunks": [{"text": "context"}]}
    judge = {"relevance": 0.3, "accuracy": 0.2, "rationale": "irrelevant"}
    prompt = build_mutation_prompt(g, trace, judge)
    assert "wrong answer" in prompt
    assert "0.3" in prompt or "0.30" in prompt
    assert "rationale" in prompt.lower()
    assert "genome" in prompt.lower() or "gene" in prompt.lower()


def test_parse_edit_response_valid_json():
    response = '''
    {
        "gene_path": "retrieval_genes.confidence_threshold",
        "new_value": 0.65,
        "rationale": "current threshold too low; missed precise queries"
    }
    '''
    edit = parse_edit_response(response)
    assert edit is not None
    assert edit["gene_path"] == "retrieval_genes.confidence_threshold"
    assert edit["new_value"] == 0.65
    assert "rationale" in edit


def test_parse_edit_response_handles_code_fence():
    response = "```json\n{\"gene_path\": \"r.r\", \"new_value\": 0.5, \"rationale\": \"x\"}\n```"
    edit = parse_edit_response(response)
    assert edit is not None
    assert edit["new_value"] == 0.5


def test_parse_edit_response_returns_none_on_invalid():
    assert parse_edit_response("not json") is None
    assert parse_edit_response('{"missing": "fields"}') is None


def test_apply_edit_modifies_specified_gene():
    g = _stub_genome()
    edit = {
        "gene_path": "retrieval_genes.confidence_threshold",
        "new_value": 0.99,
        "rationale": "test",
    }
    g2 = apply_edit(g, edit)
    assert g2.retrieval_genes.confidence_threshold == 0.99
    assert g2.retrieval_genes.embedding_model == g.retrieval_genes.embedding_model


def test_apply_edit_validates_bounds():
    g = _stub_genome()
    edit = {
        "gene_path": "retrieval_genes.confidence_threshold",
        "new_value": 1.5,
        "rationale": "broken",
    }
    g2 = apply_edit(g, edit)
    assert g2.retrieval_genes.confidence_threshold <= 1.0
