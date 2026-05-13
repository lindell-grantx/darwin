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


# --- Coordination gene additions ---

def test_pressure_response_sensitivity_default():
    c = CoordinationGenes(protocol="solo", consult_threshold=0.5,
                          timeout_ms=1000, debate_rounds=1)
    assert c.pressure_response_sensitivity == 0.5


def test_sycophancy_spectrum_signed_range():
    c_dovish = CoordinationGenes(protocol="solo", consult_threshold=0.5,
                                 timeout_ms=1000, debate_rounds=1,
                                 sycophancy_spectrum=-0.8)
    c_hawkish = CoordinationGenes(protocol="solo", consult_threshold=0.5,
                                  timeout_ms=1000, debate_rounds=1,
                                  sycophancy_spectrum=0.7)
    assert c_dovish.sycophancy_spectrum == -0.8
    assert c_hawkish.sycophancy_spectrum == 0.7


def test_confidence_calibration_default():
    c = CoordinationGenes(protocol="solo", consult_threshold=0.5,
                          timeout_ms=1000, debate_rounds=1)
    assert c.confidence_calibration == 0.5


def test_bid_aggressiveness_and_value_density():
    c = CoordinationGenes(protocol="solo", consult_threshold=0.5,
                          timeout_ms=1000, debate_rounds=1,
                          bid_aggressiveness=0.7,
                          value_density_estimator=0.4)
    assert c.bid_aggressiveness == 0.7
    assert c.value_density_estimator == 0.4


def test_capability_embedding_default_dim():
    c = CoordinationGenes(protocol="solo", consult_threshold=0.5,
                          timeout_ms=1000, debate_rounds=1)
    assert len(c.capability_embedding) == 32
    assert all(-1.0 <= v <= 1.0 for v in c.capability_embedding)


def test_marginal_contribution_threshold_default():
    c = CoordinationGenes(protocol="solo", consult_threshold=0.5,
                          timeout_ms=1000, debate_rounds=1)
    assert c.marginal_contribution_threshold == 0.0


def test_leader_candidacy_and_connection_affinity():
    c = CoordinationGenes(protocol="solo", consult_threshold=0.5,
                          timeout_ms=1000, debate_rounds=1,
                          leader_candidacy=0.8,
                          connection_affinity=[0.1, 0.2, 0.3, 0.4])
    assert c.leader_candidacy == 0.8
    assert c.connection_affinity == [0.1, 0.2, 0.3, 0.4]
