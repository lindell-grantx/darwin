"""Pass 1: per-query-class Pareto archive tests."""

from darwin.evolution.per_query_class import top_k_per_query_class


def test_top_k_per_query_class_picks_best_per_class():
    fitness = {
        ("d_a", "mongodb,vector-search"): 0.9,
        ("d_b", "mongodb,vector-search"): 0.5,
        ("d_a", "voyage,embeddings,rag"): 0.4,
        ("d_b", "voyage,embeddings,rag"): 0.85,
    }
    top1 = top_k_per_query_class(fitness, k=1)
    assert top1["mongodb,vector-search"] == ["d_a"]
    assert top1["voyage,embeddings,rag"] == ["d_b"]


def test_top_k_per_query_class_supports_k_greater_than_one():
    fitness = {
        ("d_a", "x"): 0.9,
        ("d_b", "x"): 0.7,
        ("d_c", "x"): 0.5,
    }
    top2 = top_k_per_query_class(fitness, k=2)
    assert top2["x"] == ["d_a", "d_b"]


def test_empty_input_returns_empty():
    assert top_k_per_query_class({}, k=1) == {}
