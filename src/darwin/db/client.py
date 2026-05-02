"""Async MongoDB client + change-stream helper for Darwin.

URI resolution order:
1. `MONGODB_URI` / `MONGO_URI` environment variable
2. `gcloud secrets versions access latest --secret=darwin-mongodb-uri --project=grantx-fleet`
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from typing import AsyncIterator, Optional

from motor.motor_asyncio import (
    AsyncIOMotorChangeStream,
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)


DATABASE_NAME = "darwin"
_SECRET_NAME = "darwin-mongodb-uri"
_SECRET_PROJECT = "grantx-fleet"

_client_lock = asyncio.Lock()
_client: Optional[AsyncIOMotorClient] = None


def _resolve_uri() -> str:
    uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI")
    if uri:
        return uri
    try:
        result = subprocess.run(
            [
                "gcloud",
                "secrets",
                "versions",
                "access",
                "latest",
                f"--secret={_SECRET_NAME}",
                f"--project={_SECRET_PROJECT}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            "MongoDB URI not set. Export MONGODB_URI or ensure gcloud can read "
            f"secret {_SECRET_NAME} in {_SECRET_PROJECT}."
        ) from exc
    uri = result.stdout.strip()
    if not uri:
        raise RuntimeError(f"Secret {_SECRET_NAME} returned an empty URI.")
    return uri


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
