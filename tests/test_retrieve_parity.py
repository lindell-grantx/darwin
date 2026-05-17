"""Pass 3 PR-3: parity test — legacy retrieve composition matches direct steps call.

Asserts the refactor is byte-identical: calling retrieve(query, genes) yields
the same chunks as composing the 4 steps manually with the same params.

Uses monkeypatched step functions so the test is fast + deterministic + offline.
"""

import pytest


@pytest.mark.asyncio
async def test_retrieve_composes_identical_chunks(monkeypatch):
    """Mock the underlying I/O; verify retrieve() composes the steps correctly."""
    from darwin.retrieval import retriever

    # Track step invocations
    calls = []

    async def fake_chunk_query(query, params):
        calls.append(("chunk_query", query))
        return query

    async def fake_embed_query(query, params):
        calls.append(("embed_query", query, params.get("model")))
        return [0.1, 0.2, 0.3]

    async def fake_vector_search(embedding, params):
        calls.append((
            "vector_search",
            embedding,
            params.get("top_k"),
            params.get("confidence_threshold"),
        ))
        return ["chunk_a", "chunk_b"]

    async def fake_rerank_chunks(query, chunks, params):
        calls.append(("rerank_chunks", query, list(chunks), params.get("method")))
        return list(reversed(chunks))

    monkeypatch.setattr("darwin.retrieval.steps.chunk_query", fake_chunk_query)
    monkeypatch.setattr("darwin.retrieval.steps.embed_query", fake_embed_query)
    monkeypatch.setattr("darwin.retrieval.steps.vector_search", fake_vector_search)
    monkeypatch.setattr("darwin.retrieval.steps.rerank_chunks", fake_rerank_chunks)

    genes = {
        "embedding_model": "voyage-4",
        "top_k": 7,
        "confidence_threshold": 0.4,
        "rerank": "rrf",
    }

    result = await retriever.retrieve("test query", genes)

    # Verify each step was called with expected args, in order
    assert calls[0] == ("chunk_query", "test query")
    assert calls[1] == ("embed_query", "test query", "voyage-4")
    assert calls[2] == ("vector_search", [0.1, 0.2, 0.3], 7, 0.4)
    assert calls[3][0] == "rerank_chunks"
    assert calls[3][1] == "test query"
    assert calls[3][3] == "rrf"
    # Result is rerank output, then sliced [:top_k]; top_k=7, only 2 chunks, so all returned.
    assert result == ["chunk_b", "chunk_a"]


@pytest.mark.asyncio
async def test_retrieve_top_k_override_takes_precedence(monkeypatch):
    """top_k_override arg should override genes['top_k']."""
    from darwin.retrieval import retriever

    captured = {}

    async def fake_chunk_query(q, p):
        return q

    async def fake_embed_query(q, p):
        return [0.1]

    async def fake_vector_search(emb, params):
        captured["top_k"] = params.get("top_k")
        return []

    async def fake_rerank_chunks(q, c, p):
        return c

    monkeypatch.setattr("darwin.retrieval.steps.chunk_query", fake_chunk_query)
    monkeypatch.setattr("darwin.retrieval.steps.embed_query", fake_embed_query)
    monkeypatch.setattr("darwin.retrieval.steps.vector_search", fake_vector_search)
    monkeypatch.setattr("darwin.retrieval.steps.rerank_chunks", fake_rerank_chunks)

    await retriever.retrieve("q", {"top_k": 10}, top_k_override=42)
    assert captured["top_k"] == 42
