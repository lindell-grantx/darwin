"""Gene-driven Atlas Vector Search retriever."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from darwin.retrieval.embedder import embed_query
from darwin.retrieval.reranker import rerank


MODEL_INDEXES = {
    "voyage-4": "vec_voyage_4",
    "voyage_4": "vec_voyage_4",
    "voyage-4-large": "vec_voyage_4_large",
    "voyage_4_large": "vec_voyage_4_large",
    "voyage-4-lite": "vec_voyage_4_lite",
    "voyage_4_lite": "vec_voyage_4_lite",
    "voyage-4-nano": "vec_voyage_4_nano",
    "voyage_4_nano": "vec_voyage_4_nano",
    "gemini_3072": "vec_gemini_3072",
    "gemini_1536": "vec_gemini_1536",
    "gemini_768": "vec_gemini_768",
    "gemini_256": "vec_gemini_256",
}

MODEL_PATHS = {
    "voyage-4": "embeddings.voyage_4",
    "voyage_4": "embeddings.voyage_4",
    "voyage-4-large": "embeddings.voyage_4_large",
    "voyage_4_large": "embeddings.voyage_4_large",
    "voyage-4-lite": "embeddings.voyage_4_lite",
    "voyage_4_lite": "embeddings.voyage_4_lite",
    "voyage-4-nano": "embeddings.voyage_4_nano",
    "voyage_4_nano": "embeddings.voyage_4_nano",
    "gemini_3072": "embeddings.gemini_3072",
    "gemini_1536": "embeddings.gemini_1536",
    "gemini_768": "embeddings.gemini_768",
    "gemini_256": "embeddings.gemini_256",
}


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    text: str
    score: float


def _db() -> Any:
    uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI")
    if not uri:
        raise RuntimeError("Missing MONGODB_URI/MONGO_URI for retrieval")
    client = AsyncIOMotorClient(uri)
    return client[os.environ.get("DB_NAME", "darwin")]


def _gene(genes: dict[str, Any], name: str, default: Any) -> Any:
    return genes.get(name, default)


def _transform_query(query: str, transform: str) -> str:
    if transform == "hyde":
        return f"Hypothetical answer to retrieve evidence for: {query}"
    if transform == "step_back":
        return f"What broader concepts are needed to answer: {query}"
    if transform == "multi_query":
        return f"{query}\nAlternative phrasing: explain implementation details and tradeoffs."
    return query


def build_vector_pipeline(query_vector: list[float], genes: dict[str, Any], top_k: int) -> list[dict[str, Any]]:
    model = _gene(genes, "embedding_model", "voyage-4")
    return [
        {
            "$vectorSearch": {
                "index": MODEL_INDEXES.get(model, f"vec_{str(model).replace('-', '_')}"),
                "path": MODEL_PATHS.get(model, f"embeddings.{str(model).replace('-', '_')}"),
                "queryVector": query_vector,
                "numCandidates": max(100, top_k * 20),
                "limit": top_k * 2,
            }
        },
        {
            "$project": {
                "_id": 1,
                "text": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]


async def retrieve(query: str, genes: dict[str, Any], top_k_override: int | None = None) -> list[RetrievedChunk]:
    """Gene-driven retrieval pipeline over the chunks collection."""
    model = _gene(genes, "embedding_model", "voyage-4")
    top_k = int(top_k_override or _gene(genes, "top_k", 5))
    threshold = float(_gene(genes, "confidence_threshold", 0.0))
    transformed = _transform_query(query, str(_gene(genes, "query_transform", "none")))
    query_vector = await embed_query(transformed, model)

    cursor = _db().chunks.aggregate(build_vector_pipeline(query_vector, genes, top_k))
    raw_chunks = await cursor.to_list(length=top_k * 2)

    chunks = [
        RetrievedChunk(
            chunk_id=str(item.get("_id") or item.get("id")),
            text=str(item.get("text", "")),
            score=float(item.get("score", 0.0)),
        )
        for item in raw_chunks
        if float(item.get("score", 0.0)) >= threshold
    ]

    ordered = await rerank(query, chunks, str(_gene(genes, "rerank", "none")))
    return ordered[:top_k]
