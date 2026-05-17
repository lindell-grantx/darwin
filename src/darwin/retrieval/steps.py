"""Pass 3: discrete retrieval steps that compose into retriever.retrieve().

Splits monolithic retrieve() into 4 async callables so pipeline_runner can
walk a DAG topologically:

- chunk_query(query, params) -> str — query-side rewriting (no-op in Pass 3)
- embed_query(query, params) -> list[float] — Voyage embedding via embedder
- vector_search(embedding, params) -> list[RetrievedChunk] — Atlas $vectorSearch
- rerank_chunks(query, chunks, params) -> list[RetrievedChunk] — reranker pass

retriever.retrieve() composes these — zero behavior change for legacy callers.
"""

from __future__ import annotations

from typing import Any


async def chunk_query(query: str, params: dict[str, Any]) -> str:
    """Query-side rewriting placeholder. No-op in Pass 3, hook for future."""
    return query


async def embed_query(query: str, params: dict[str, Any]) -> list[float]:
    """Embed query using params.model (default voyage-4).

    Delegates to embedder.embed_query to preserve the per-process run cache
    used by the legacy path.
    """
    from darwin.retrieval.embedder import embed_query as _embed_query

    model = params.get("model", "voyage-4")
    return await _embed_query(query, model)


async def vector_search(
    embedding: list[float], params: dict[str, Any]
):
    """Atlas $vectorSearch with embedding + retrieval params.

    Calls into retriever._run_vector_search (extracted helper). Returns
    list[RetrievedChunk] — same shape as legacy retrieve() output.
    """
    from darwin.retrieval.retriever import _run_vector_search

    return await _run_vector_search(
        embedding=embedding,
        genes=params.get("genes", {}),
        top_k=params.get("top_k", 10),
        confidence_threshold=params.get("confidence_threshold", 0.0),
    )


async def rerank_chunks(
    query: str,
    chunks: list,
    params: dict[str, Any],
):
    """Apply rerank method if params.method != 'none'."""
    method = params.get("method", "none")
    if method in {"", "none", None}:
        return chunks
    from darwin.retrieval.reranker import rerank

    return await rerank(query, chunks, method=method)
