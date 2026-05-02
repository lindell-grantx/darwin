"""Idempotent collection + index setup for the Darwin database.

Run as a script:
    python -m darwin.db.indexes
or import and call `await ensure_collections(db)` then `await ensure_indexes(db)`.

The four vector indexes are keyed to Voyage model variants. Each chunk doc
carries an `embeddings` sub-document with one vector per model under a field
key matching the model name (hyphens → underscores). Embedding generation
happens client-side during seeding (Atlas's auto-embed feature is gated by
org policy on this hackathon project).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import CollectionInvalid, OperationFailure

from darwin.db.client import close_client, get_db
from darwin.db.schemas import (
    COLLECTION_CHAMPIONS,
    COLLECTION_CHUNKS,
    COLLECTION_FITNESS_EVALUATIONS,
    COLLECTION_GENERATIONS,
    COLLECTION_GENOMES,
    COLLECTION_QUERIES,
    EMBEDDING_DIMS,
    EMBEDDING_MODELS,
    model_to_field,
)


log = logging.getLogger(__name__)


def _vector_index(model: str) -> dict[str, Any]:
    field = model_to_field(model)
    return {
        "name": f"vec_{field}",
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": f"embeddings.{field}",
                    "numDimensions": EMBEDDING_DIMS[model],
                    "similarity": "cosine",
                }
            ]
        },
    }


VECTOR_INDEXES: list[dict[str, Any]] = [_vector_index(m) for m in EMBEDDING_MODELS]


async def ensure_collections(db: AsyncIOMotorDatabase) -> list[str]:
    """Create the six collections idempotently. Returns the list created."""

    existing = set(await db.list_collection_names())
    created: list[str] = []

    standard = [
        COLLECTION_GENOMES,
        COLLECTION_CHUNKS,
        COLLECTION_QUERIES,
        COLLECTION_FITNESS_EVALUATIONS,
        COLLECTION_CHAMPIONS,
    ]
    for name in standard:
        if name in existing:
            continue
        try:
            await db.create_collection(name)
            created.append(name)
        except CollectionInvalid:
            pass

    if COLLECTION_GENERATIONS not in existing:
        try:
            await db.create_collection(
                COLLECTION_GENERATIONS,
                timeseries={
                    "timeField": "created_at",
                    "metaField": "generation",
                    "granularity": "minutes",
                },
            )
            created.append(COLLECTION_GENERATIONS)
        except CollectionInvalid:
            pass

    return created


async def ensure_indexes(db: AsyncIOMotorDatabase) -> dict[str, list[str]]:
    """Create regular + vector indexes idempotently. Returns names per collection."""

    out: dict[str, list[str]] = {}

    out[COLLECTION_GENOMES] = await db[COLLECTION_GENOMES].create_indexes(
        _models(
            [
                ([("status", ASCENDING), ("generation", DESCENDING)], "status_generation"),
                ([("generation", ASCENDING)], "generation"),
                ([("parent_ids", ASCENDING)], "parent_ids"),
                ([("fitness.composite", DESCENDING)], "fitness_composite"),
            ]
        )
    )

    out[COLLECTION_CHUNKS] = await db[COLLECTION_CHUNKS].create_indexes(
        _models(
            [
                ([("doc_id", ASCENDING), ("position", ASCENDING)], "doc_position"),
                ([("source", ASCENDING)], "source"),
            ]
        )
    )

    # NOTE: queries indexes are owned by scripts/seed_queries.py, which creates
    # them under pymongo's default names. Don't duplicate them here — the names
    # would conflict and one side would crash.
    out[COLLECTION_QUERIES] = []

    out[COLLECTION_FITNESS_EVALUATIONS] = await db[
        COLLECTION_FITNESS_EVALUATIONS
    ].create_indexes(
        _models(
            [
                ([("generation", ASCENDING)], "generation"),
                ([("genome_id", ASCENDING), ("generation", ASCENDING)], "genome_generation"),
                ([("run_id", ASCENDING)], "run_id"),
                ([("timestamp", DESCENDING)], "timestamp"),
            ]
        )
    )

    out[COLLECTION_CHAMPIONS] = await db[COLLECTION_CHAMPIONS].create_indexes(
        _models(
            [
                ([("genome_id", ASCENDING)], "genome_id", {"unique": True}),
                ([("promoted_at_generation", DESCENDING)], "promoted_at_generation"),
            ]
        )
    )

    out[f"{COLLECTION_CHUNKS}::vector"] = await _ensure_vector_indexes(db)

    return out


async def _ensure_vector_indexes(db: AsyncIOMotorDatabase) -> list[str]:
    coll = db[COLLECTION_CHUNKS]
    try:
        existing_cursor = await coll.list_search_indexes().to_list(length=None)
        existing = {idx["name"]: idx for idx in existing_cursor}
    except OperationFailure as exc:
        log.warning("list_search_indexes failed (%s); attempting create anyway.", exc)
        existing = {}

    for name, idx in list(existing.items()):
        if idx.get("status") == "FAILED":
            log.info("dropping FAILED vector index %s before recreate", name)
            try:
                await coll.drop_search_index(name)
                existing.pop(name, None)
            except OperationFailure as exc:
                log.warning("drop %s failed: %s", name, exc)

    created: list[str] = []
    for spec in VECTOR_INDEXES:
        if spec["name"] in existing:
            continue
        try:
            await coll.create_search_index(model=spec)
            created.append(spec["name"])
        except OperationFailure as exc:
            if "already exists" in str(exc).lower():
                continue
            raise
    return created


def _models(entries: list) -> list:
    from pymongo import IndexModel

    out = []
    for entry in entries:
        if len(entry) == 2:
            keys, name = entry
            opts: dict[str, Any] = {}
        else:
            keys, name, opts = entry
        out.append(IndexModel(keys, name=name, **opts))
    return out


async def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    db = await get_db()
    created_collections = await ensure_collections(db)
    log.info("collections created: %s", created_collections or "(none — already present)")
    created_indexes = await ensure_indexes(db)
    for collection, names in created_indexes.items():
        log.info("indexes on %s: %s", collection, names or "(already present)")
    await close_client()


if __name__ == "__main__":
    asyncio.run(_main())
