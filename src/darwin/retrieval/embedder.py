"""Voyage embedding wrapper with batching + rate-limit backoff.

API key resolution: `VOYAGE_API_KEY` env var, falling back to
`gcloud secrets versions access latest --secret=darwin-voyage-key
--project=grantx-fleet`.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from typing import Optional

import voyageai


log = logging.getLogger(__name__)

VOYAGE_BATCH_SIZE = 128
MAX_RETRIES = 6
INITIAL_BACKOFF_SEC = 2.0
MAX_BACKOFF_SEC = 60.0


def _resolve_api_key() -> str:
    key = os.environ.get("VOYAGE_API_KEY")
    if key:
        return key
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
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            "Voyage API key not set. Export VOYAGE_API_KEY or ensure gcloud "
            "can read secret darwin-voyage-key in grantx-fleet."
        ) from exc
    key = result.stdout.strip()
    if not key:
        raise RuntimeError("Secret darwin-voyage-key returned empty.")
    return key


_client: Optional[voyageai.Client] = None


def get_client() -> voyageai.Client:
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=_resolve_api_key())
    return _client


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "rate" in msg or "429" in msg or "throttle" in msg or "quota" in msg


def _embed_with_retry(
    texts: list[str], model: str, input_type: str
) -> list[list[float]]:
    backoff = INITIAL_BACKOFF_SEC
    last_exc: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = get_client().embed(texts, model=model, input_type=input_type)
            return list(response.embeddings)
        except Exception as exc:
            last_exc = exc
            if _is_rate_limit(exc) and attempt < MAX_RETRIES:
                log.warning(
                    "voyage rate-limit on %s (attempt %d/%d); sleeping %.1fs",
                    model,
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


def embed_documents(texts: list[str], model: str) -> list[list[float]]:
    """Embed a list of documents with one model. Batches at VOYAGE_BATCH_SIZE."""

    if not texts:
        return []
    out: list[list[float]] = []
    for start in range(0, len(texts), VOYAGE_BATCH_SIZE):
        batch = texts[start : start + VOYAGE_BATCH_SIZE]
        out.extend(_embed_with_retry(batch, model, "document"))
    return out


def embed_query(text: str, model: str) -> list[float]:
    """Embed a single query string. Used at retrieval time."""

    return _embed_with_retry([text], model, "query")[0]
