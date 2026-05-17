"""Pass 3 PR-4: DAG branching + fuse semantics."""

import pytest

from darwin.genome.pipeline import PipelineEdge, PipelineNode, RetrievalPipeline


def test_branching_topology_validates():
    """A node with two downstream edges (fan-out) is valid."""
    chunk = PipelineNode(stage="chunk", operator="fixed_size")
    embed_a = PipelineNode(stage="embed", operator="voyage_4")
    embed_b = PipelineNode(stage="embed", operator="voyage_4_large")
    retrieve_a = PipelineNode(stage="retrieve", operator="vector")
    retrieve_b = PipelineNode(stage="retrieve", operator="vector")
    fuse = PipelineNode(stage="fuse", operator="rrf")
    p = RetrievalPipeline(
        nodes=[chunk, embed_a, embed_b, retrieve_a, retrieve_b, fuse],
        edges=[
            PipelineEdge(from_id=chunk.node_id, to_id=embed_a.node_id),
            PipelineEdge(from_id=chunk.node_id, to_id=embed_b.node_id),
            PipelineEdge(from_id=embed_a.node_id, to_id=retrieve_a.node_id),
            PipelineEdge(from_id=embed_b.node_id, to_id=retrieve_b.node_id),
            PipelineEdge(from_id=retrieve_a.node_id, to_id=fuse.node_id),
            PipelineEdge(from_id=retrieve_b.node_id, to_id=fuse.node_id),
        ],
    )
    p.validate_dag()


@pytest.mark.asyncio
async def test_execute_pipeline_handles_simple_fanout(monkeypatch):
    """Two parallel embed branches fan out from chunk, fuse merges."""
    from darwin.agents.pipeline_runner import execute_pipeline

    invocations: list[str] = []

    async def fake_chunk_query(query, params):
        invocations.append(f"chunk:{query}")
        return query

    async def fake_embed_query(query, params):
        model = params.get("model", "voyage-4")
        invocations.append(f"embed:{model}")
        return [1.0 if "large" not in model else 2.0]

    async def fake_vector_search(embedding, params):
        return [f"chunk_from_{embedding[0]}"]

    async def fake_rerank_chunks(query, chunks, params):
        return chunks

    monkeypatch.setattr("darwin.retrieval.steps.chunk_query", fake_chunk_query)
    monkeypatch.setattr("darwin.retrieval.steps.embed_query", fake_embed_query)
    monkeypatch.setattr("darwin.retrieval.steps.vector_search", fake_vector_search)
    monkeypatch.setattr("darwin.retrieval.steps.rerank_chunks", fake_rerank_chunks)

    async def fake_vertex(system, user, max_tokens, thinking=False):
        return "answer"
    monkeypatch.setattr("darwin.llm.vertex.vertex_complete", fake_vertex)

    chunk = PipelineNode(stage="chunk", operator="fixed_size")
    embed_a = PipelineNode(stage="embed", operator="voyage_4")
    embed_b = PipelineNode(stage="embed", operator="voyage_4_large")
    retrieve_a = PipelineNode(stage="retrieve", operator="vector")
    retrieve_b = PipelineNode(stage="retrieve", operator="vector")
    fuse = PipelineNode(stage="fuse", operator="rrf")
    generate = PipelineNode(stage="generate", operator="claude_haiku")

    p = RetrievalPipeline(
        nodes=[chunk, embed_a, embed_b, retrieve_a, retrieve_b, fuse, generate],
        edges=[
            PipelineEdge(from_id=chunk.node_id, to_id=embed_a.node_id),
            PipelineEdge(from_id=chunk.node_id, to_id=embed_b.node_id),
            PipelineEdge(from_id=embed_a.node_id, to_id=retrieve_a.node_id),
            PipelineEdge(from_id=embed_b.node_id, to_id=retrieve_b.node_id),
            PipelineEdge(from_id=retrieve_a.node_id, to_id=fuse.node_id),
            PipelineEdge(from_id=retrieve_b.node_id, to_id=fuse.node_id),
            PipelineEdge(from_id=fuse.node_id, to_id=generate.node_id),
        ],
    )

    await execute_pipeline(p, "q", db=None)

    embed_models_called = [i for i in invocations if i.startswith("embed:")]
    assert len(embed_models_called) == 2
