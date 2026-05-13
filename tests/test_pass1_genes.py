"""Pass 1: validate 8 new retrieval + 8 new coordination genes."""

import pytest

from darwin.db.schemas import CoordinationGenes, RetrievalGenes


# --- Retrieval gene additions ---

def test_retrieval_mode_router_default_and_set():
    r = RetrievalGenes(
        embedding_model="voyage-4", chunk_size=512, chunk_overlap=0.1,
        query_transform="none", rerank="none", confidence_threshold=0.5,
        top_k=10, source_routing=["mongodb"],
    )
    assert r.retrieval_mode_router == "single_shot"
    r2 = RetrievalGenes(
        embedding_model="voyage-4", chunk_size=512, chunk_overlap=0.1,
        query_transform="none", rerank="none", confidence_threshold=0.5,
        top_k=10, source_routing=["mongodb"], retrieval_mode_router="agentic",
    )
    assert r2.retrieval_mode_router == "agentic"


def test_hierarchical_traversal_default():
    r = RetrievalGenes(
        embedding_model="voyage-4", chunk_size=512, chunk_overlap=0.1,
        query_transform="none", rerank="none", confidence_threshold=0.5,
        top_k=10, source_routing=["mongodb"],
    )
    assert r.hierarchical_traversal_strategy == "single_level"


def test_graph_construction_genes():
    r = RetrievalGenes(
        embedding_model="voyage-4", chunk_size=512, chunk_overlap=0.1,
        query_transform="none", rerank="none", confidence_threshold=0.5,
        top_k=10, source_routing=["mongodb"],
        graph_construction_mode="entity_relation",
        graph_eagerness=0.3,
    )
    assert r.graph_construction_mode == "entity_relation"
    assert r.graph_eagerness == 0.3


def test_embedding_compression_genes():
    r = RetrievalGenes(
        embedding_model="voyage-4", chunk_size=512, chunk_overlap=0.1,
        query_transform="none", rerank="none", confidence_threshold=0.5,
        top_k=10, source_routing=["mongodb"],
        embedding_compression_dim=320,
        embedding_quantization="int8",
    )
    assert r.embedding_compression_dim == 320
    assert r.embedding_quantization == "int8"


def test_retrieval_tool_set_default_is_semantic_only():
    r = RetrievalGenes(
        embedding_model="voyage-4", chunk_size=512, chunk_overlap=0.1,
        query_transform="none", rerank="none", confidence_threshold=0.5,
        top_k=10, source_routing=["mongodb"],
    )
    assert r.retrieval_tool_set == ["semantic_search"]


def test_context_utilization_ratio_default_is_one():
    r = RetrievalGenes(
        embedding_model="voyage-4", chunk_size=512, chunk_overlap=0.1,
        query_transform="none", rerank="none", confidence_threshold=0.5,
        top_k=10, source_routing=["mongodb"],
    )
    assert r.context_utilization_ratio == 1.0


def test_context_utilization_bounds():
    with pytest.raises(Exception):
        RetrievalGenes(
            embedding_model="voyage-4", chunk_size=512, chunk_overlap=0.1,
            query_transform="none", rerank="none", confidence_threshold=0.5,
            top_k=10, source_routing=["mongodb"],
            context_utilization_ratio=1.5,
        )
