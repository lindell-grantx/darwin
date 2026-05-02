"""Voyage embedding wrapper.

Combines:
- Async public API (`embed_query`, `embed_batch`) used by the retriever and
  agent runner.
- Sync convenience wrapper (`embed_documents`) used by the seed script.
- Per-process run cache so a query embedded once is reused across genome
  evaluations.
- Model-name aliases so callers can pass either underscored field-name form
  ("voyage_4_large") or canonical Voyage form ("voyage-4-large").
- Automatic 128-doc batching to stay under Voyage's per-request input cap.
- Exponential backoff on rate-limit / quota errors.
- API key resolution: `VOYAGE_API_KEY` env var, falling back to
  `gcloud secrets versions access latest --secret=darwin-voyage-key
  --project=grantx-fleet`.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from typing import Optional


log = logging.getLogger(__name__)

VOYAGE_BATCH_SIZE = 128
MAX_RETRIES = 6
INITIAL_BACKOFF_SEC = 2.0
MAX_BACKOFF_SEC = 60.0


_MODEL_ALIASES: dict[str, str] = {
    "voyage_4": "voyage-4",
    "voyage_4_large": "voyage-4-large",
    "voyage_4_lite": "voyage-4-lite",
    "voyage_4_nano": "voyage-4-nano",
    "voyage_code_3": "voyage-code-3",
    # Legacy Gemini-era keys mapped to current Voyage equivalents.
    "gemini_3072": "voyage-4-large",
    "gemini_1536": "voyage-4",
    "gemini_768": "voyage-4-lite",
    "gemini_256": "voyage-4-nano",
}


def _voyage_model_name(model: str) -> str:
    return _MODEL_ALIASES.get(model, model)


_api_key_cache: Optional[str] = None
_RUN_CACHE: dict[tuple[str, str], list[float]] = {}


def _resolve_api_key() -> str:
    global _api_key_cache
    if _api_key_cache is not None:
        return _api_key_cache
    key = os.environ.get("VOYAGE_API_KEY")
    if not key:
        try:
            result = subprocess.run(
                [
                    "gcloud",
                    "secrets",
                    "versions",
                    "access",
                    "latest",
                    "--secret=darwin-voyage-key",
                    "--project=grantx-fleet",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            key = result.stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise RuntimeError(
                "Voyage API key not set. Export VOYAGE_API_KEY or ensure gcloud "
                "can read secret darwin-voyage-key in grantx-fleet."
            ) from exc
    if not key:
        raise RuntimeError("Voyage API key resolution returned empty.")
    _api_key_cache = key
    return key


_voyage_client = None


def _get_client():
    global _voyage_client
    if _voyage_client is not None:
        return _voyage_client
    try:
        import voyageai
    except ModuleNotFoundError as exc:
        raise RuntimeError("Install voyageai to use Voyage embeddings") from exc
    _voyage_client = voyageai.Client(api_key=_resolve_api_key())
    return _voyage_client


def clear_run_cache() -> None:
    _RUN_CACHE.clear()


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(token in msg for token in ("rate", "429", "throttle", "quota"))


def _embed_sync_with_retry(
    texts: list[str], model: str, input_type: str
) -> list[list[float]]:
    canonical = _voyage_model_name(model)
    backoff = INITIAL_BACKOFF_SEC
    last_exc: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = _get_client().embed(texts, model=canonical, input_type=input_type)
            return [list(v) for v in response.embeddings]
        except Exception as exc:
            last_exc = exc
            if _is_rate_limit(exc) and attempt < MAX_RETRIES:
                log.warning(
                    "voyage rate-limit on %s (attempt %d/%d); sleeping %.1fs",
                    canonical,
                    attempt,
                    MAX_RETRIES,
                    backoff,
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF_SEC)
                continue
            raise
    assert last_exc is not None
    raise last_exc


def _batched(texts: list[str], model: str, input_type: str) -> list[list[float]]:
    if not texts:
        return []
    out: list[list[float]] = []
    for start in range(0, len(texts), VOYAGE_BATCH_SIZE):
        chunk = texts[start : start + VOYAGE_BATCH_SIZE]
        out.extend(_embed_sync_with_retry(chunk, model, input_type))
    return out


# ------------------------------------------------------------------ public API


def embed_documents(texts: list[str], model: str) -> list[list[float]]:
    """Sync batch embedding for documents (corpus seeding).

    Used by `scripts/seed_corpus.py`. Wrap in `asyncio.to_thread` if you need
    to call this from an async context.
    """

    return _batched(texts, model, "document")


async def embed_batch(
    texts: list[str], model: str, *, input_type: str = "document"
) -> list[list[float]]:
    """Async batch embedding. Default input_type is `document`.

    Pass `input_type="query"` when embedding a search query so Voyage applies
    query-side preprocessing.
    """

    return await asyncio.to_thread(_batched, texts, model, input_type)


async def embed_query(text: str, model: str) -> list[float]:
    """Single query embedding, cached per-process by (text, model)."""

    cache_key = (text, model)
    if cache_key not in _RUN_CACHE:
        [embedding] = await embed_batch([text], model, input_type="query")
        _RUN_CACHE[cache_key] = embedding
    return _RUN_CACHE[cache_key]
