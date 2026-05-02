"""Reranking helpers for retrieved chunks."""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from darwin.retrieval.retriever import RetrievedChunk


async def rerank(query: str, chunks: list["RetrievedChunk"], method: str) -> list["RetrievedChunk"]:
    if method in {"", "none", None}:
        return chunks
    if method in {"rrf", "reciprocal_rank_fusion"}:
        return _rrf(chunks)
    if method in {"voyage_rerank_2", "voyage-rerank-2", "llm_rerank", "cross_encoder"}:
        return await _voyage_rerank(query, chunks)
    return chunks


def _rrf(chunks: list["RetrievedChunk"]) -> list["RetrievedChunk"]:
    scored = []
    for rank, chunk in enumerate(chunks, start=1):
        scored.append((chunk.score + 1.0 / (60 + rank), chunk))
    return [chunk for _, chunk in sorted(scored, key=lambda item: item[0], reverse=True)]


async def _voyage_rerank(query: str, chunks: list["RetrievedChunk"]) -> list["RetrievedChunk"]:
    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key or not chunks:
        return chunks

    def run_rerank() -> list["RetrievedChunk"]:
        try:
            import voyageai
        except ModuleNotFoundError:
            return chunks

        client = voyageai.Client(api_key=api_key)
        response = client.rerank(
            query=query,
            documents=[chunk.text for chunk in chunks],
            model="rerank-2",
            top_k=len(chunks),
        )
        return [chunks[item.index] for item in response.results]

    return await asyncio.to_thread(run_rerank)
