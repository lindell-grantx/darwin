"""Async MongoDB client + change-stream helper for Darwin.

URI resolution order:
1. `MONGODB_URI` / `MONGO_URI` environment variable
2. GCP Secret Manager via `DARWIN_GCP_SECRET_PROJECT` (see darwin.lib.secrets)
"""

from __future__ import annotations

import asyncio
import os
from typing import AsyncIterator, Optional

from motor.motor_asyncio import (
    AsyncIOMotorChangeStream,
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

from darwin.lib.secrets import resolve_gcp_secret


DATABASE_NAME = "darwin"

_client_lock = asyncio.Lock()
_client: Optional[AsyncIOMotorClient] = None


def _resolve_uri() -> str:
    uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI")
    if uri:
        return uri
    uri = resolve_gcp_secret("darwin-mongodb-uri")
    if uri:
        return uri
    raise RuntimeError(
        "MongoDB URI not set. Export MONGODB_URI or set "
        "DARWIN_GCP_SECRET_PROJECT to use gcloud secret resolution."
    )


async def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is not None:
        return _client
    async with _client_lock:
        if _client is None:
            _client = AsyncIOMotorClient(_resolve_uri(), tz_aware=True)
    return _client


async def get_db(name: str = DATABASE_NAME) -> AsyncIOMotorDatabase:
    client = await get_client()
    return client[name]


async def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def watch_collection(
    collection: AsyncIOMotorCollection,
    *,
    operation_types: tuple[str, ...] = ("insert",),
    full_document: str = "updateLookup",
) -> AsyncIterator[dict]:
    """Yield change-stream events for `collection`. Caller handles retries."""

    pipeline = [{"$match": {"operationType": {"$in": list(operation_types)}}}]
    stream: AsyncIOMotorChangeStream
    async with collection.watch(pipeline, full_document=full_document) as stream:
        async for change in stream:
            yield change
