"""v2 MVP: validate new genes added to existing schemas."""

from darwin.db.schemas import CoordinationGenes, RetrievalGenes


def test_coordination_genes_has_signal_decay_rate():
    c = CoordinationGenes(
        protocol="solo",
        consult_threshold=0.5,
        timeout_ms=1000,
        debate_rounds=1,
        signal_decay_rate=0.5,
    )
    assert c.signal_decay_rate == 0.5


def test_signal_decay_rate_default_is_one():
    c = CoordinationGenes(
        protocol="solo",
        consult_threshold=0.5,
        timeout_ms=1000,
        debate_rounds=1,
    )
    assert c.signal_decay_rate == 1.0


def test_retrieval_genes_has_search_depth_policy():
    r = RetrievalGenes(
        embedding_model="voyage-4",
        chunk_size=512,
        chunk_overlap=0.1,
        query_transform="none",
        rerank="none",
        confidence_threshold=0.5,
        top_k=10,
        source_routing=["mongodb"],
        search_depth_policy=0.7,
    )
    assert r.search_depth_policy == 0.7


def test_search_depth_policy_default_is_half():
    r = RetrievalGenes(
        embedding_model="voyage-4",
        chunk_size=512,
        chunk_overlap=0.1,
        query_transform="none",
        rerank="none",
        confidence_threshold=0.5,
        top_k=10,
        source_routing=["mongodb"],
    )
    assert r.search_depth_policy == 0.5
