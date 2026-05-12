#!/usr/bin/env python
"""Seed query_type_buckets by computing centroid Voyage-4 embeddings per tag tuple.

For each unique `domain_tags` tuple in eval_queries.json, embed the constituent
queries (concatenated text), average them, and write a QueryTypeBucket.

Usage:
    MONGODB_URI=... VOYAGE_API_KEY=... python scripts/seed_query_type_buckets.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from darwin.db.client import close_client, get_db  # noqa: E402
from darwin.db.schemas import COLLECTION_QUERY_TYPE_BUCKETS, QueryTypeBucket  # noqa: E402
from darwin.lib.secrets import resolve_gcp_secret  # noqa: E402
from darwin.retrieval.embedder import embed_batch  # noqa: E402


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("seed_buckets")


EVAL_QUERIES_PATH = Path(__file__).resolve().parents[1] / "scripts" / "eval_queries.json"
EMBEDDING_MODEL = "voyage-4"


def _avg(vectors: list[list[float]]) -> list[float]:
    n = len(vectors)
    dim = len(vectors[0])
    out = [0.0] * dim
    for v in vectors:
        for i, x in enumerate(v):
            out[i] += x
    return [x / n for x in out]


async def main() -> None:
    if not os.environ.get("MONGODB_URI"):
        uri = resolve_gcp_secret("darwin-mongodb-uri")
        if uri:
            os.environ["MONGODB_URI"] = uri
    if not os.environ.get("VOYAGE_API_KEY"):
        key = resolve_gcp_secret("darwin-voyage-key")
        if key:
            os.environ["VOYAGE_API_KEY"] = key

    queries = json.loads(EVAL_QUERIES_PATH.read_text(encoding="utf-8"))

    by_tag: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for q in queries:
        tag = tuple(q["domain_tags"])
        by_tag[tag].append(q["text"])

    log.info("found %d unique tag tuples across %d queries", len(by_tag), len(queries))

    db = await get_db()
    coll = db[COLLECTION_QUERY_TYPE_BUCKETS]

    deleted = await coll.delete_many({})
    log.info("deleted %d existing buckets", deleted.deleted_count)

    docs = []
    for tag, texts in by_tag.items():
        log.info("embedding %d queries for tag %s", len(texts), tag)
        embeds = await embed_batch(texts, EMBEDDING_MODEL)
        centroid = _avg(embeds)
        bucket = QueryTypeBucket(
            bucket_key=tag,
            embedding=centroid,
            n_queries=len(texts),
        )
        docs.append(bucket.model_dump(mode="json", by_alias=True))

    if docs:
        await coll.insert_many(docs)
    log.info("inserted %d query type buckets", len(docs))

    await close_client()


if __name__ == "__main__":
    asyncio.run(main())
