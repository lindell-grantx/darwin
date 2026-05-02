"""Embedding helpers for query and corpus text."""

from __future__ import annotations

import asyncio
import os


_RUN_CACHE: dict[tuple[str, str], list[float]] = {}


def _voyage_model_name(model: str) -> str:
    aliases = {
        "voyage_4": "voyage-4",
        "voyage_4_large": "voyage-4-large",
        "voyage_4_lite": "voyage-4-lite",
        "voyage_4_nano": "voyage-4-nano",
        "gemini_3072": "voyage-4-large",
        "gemini_1536": "voyage-4",
        "gemini_768": "voyage-4-lite",
        "gemini_256": "voyage-4-nano",
    }
    return aliases.get(model, model)


def clear_run_cache() -> None:
    _RUN_CACHE.clear()


async def embed_query(text: str, model: str) -> list[float]:
    """Single query embedding cached by text/model for one process run."""
    cache_key = (text, model)
    if cache_key not in _RUN_CACHE:
        [embedding] = await embed_batch([text], model)
        _RUN_CACHE[cache_key] = embedding
    return _RUN_CACHE[cache_key]


async def embed_batch(texts: list[str], model: str) -> list[list[float]]:
    """Batch embeddings through Voyage."""
    if not texts:
        return []

    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing VOYAGE_API_KEY for embedding")

    def run_embed() -> list[list[float]]:
        try:
            import voyageai
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install voyageai to use Voyage embeddings") from exc

        client = voyageai.Client(api_key=api_key)
        response = client.embed(texts, model=_voyage_model_name(model), input_type="query")
        return [list(item) for item in response.embeddings]

    return await asyncio.to_thread(run_embed)
