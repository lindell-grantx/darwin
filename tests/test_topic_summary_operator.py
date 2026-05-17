"""Pass 3 PR-4: topic_summary operator (LightRAG-lazy clustering)."""

from darwin.retrieval.operators.topic_summary import (
    CLUSTER_MIN_SIZE,
    COSINE_THRESHOLD,
    MAX_INPUT_CHUNKS,
    cluster_chunks_by_embedding,
)


def test_constants_documented():
    assert CLUSTER_MIN_SIZE == 3
    assert COSINE_THRESHOLD == 0.7
    assert MAX_INPUT_CHUNKS == 50


def test_cluster_chunks_groups_similar_embeddings():
    chunks = [
        {"id": "a", "embedding": [1.0, 0.0, 0.0]},
        {"id": "b", "embedding": [0.99, 0.05, 0.0]},
        {"id": "c", "embedding": [0.0, 1.0, 0.0]},
        {"id": "d", "embedding": [0.05, 0.99, 0.0]},
    ]
    clusters = cluster_chunks_by_embedding(chunks)
    cluster_ids = [{c["id"] for c in cl} for cl in clusters]
    assert {"a", "b"} in cluster_ids
    assert {"c", "d"} in cluster_ids


def test_cluster_chunks_respects_singletons():
    chunks = [
        {"id": "a", "embedding": [1.0, 0.0]},
        {"id": "b", "embedding": [-1.0, 0.0]},
    ]
    clusters = cluster_chunks_by_embedding(chunks)
    assert len(clusters) == 2
    assert all(len(c) == 1 for c in clusters)


def test_cluster_chunks_caps_input():
    chunks = [{"id": f"c{i}", "embedding": [float(i)]} for i in range(60)]
    clusters = cluster_chunks_by_embedding(chunks)
    total_chunks = sum(len(c) for c in clusters)
    assert total_chunks <= MAX_INPUT_CHUNKS
