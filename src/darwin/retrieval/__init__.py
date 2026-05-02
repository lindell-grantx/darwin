"""Retrieval primitives for Darwin genome evaluation."""

from darwin.retrieval.embedder import (
    clear_run_cache,
    embed_batch,
    embed_documents,
    embed_query,
)
from darwin.retrieval.retriever import RetrievedChunk, retrieve

__all__ = [
    "RetrievedChunk",
    "clear_run_cache",
    "embed_batch",
    "embed_documents",
    "embed_query",
    "retrieve",
]
