"""Inference-time routing: pick the defender genome for an incoming query.

Both the async worker (`scripts/run_query_worker.py`) and the FastAPI handlers
(`darwin.api.server`'s `/evaluate`, `/evaluate-stream`) need the same defender-
selection logic, so it lives here.

The public entry point is `route_query(db, text)`. It returns
`(routing_dict, defender_genome)` where:

  - `routing_dict` matches the v2 telemetry schema (always shaped, with nulls
    where inputs are unavailable):
      {
        "bucket_key":          list[str] | None,
        "cosine":              float     | None,
        "nash_strategy_id":    str       | None,
        "sampled_defender_id": str       | None,
      }
  - `defender_genome` is the raw Mongo document for the chosen genome, or
    None if no usable genome exists at all (caller surfaces as failure).

Fallback ladder:
  - Buckets seeded   -> embed the query (Voyage-4) and pick best-cosine bucket.
                        Embedding/routing failures degrade silently.
  - NashStrategy set -> sample a defender id by weight; look up the genome.
                        Stale id (genome not in collection) -> fall back.
  - Genesis state    -> highest-fitness alive/champion genome (v1 behavior).
"""

from __future__ import annotations

import logging
import random
from typing import Any

from darwin.api.routing import cosine_similarity, route_query_to_bucket
from darwin.db.schemas import (
    COLLECTION_GENOMES,
    COLLECTION_NASH_STRATEGIES,
    COLLECTION_QUERY_TYPE_BUCKETS,
    NashStrategy,
    QueryTypeBucket,
)
from darwin.retrieval.embedder import embed_batch


log = logging.getLogger("darwin.api.inference_routing")


async def pick_highest_fitness_genome(db) -> dict[str, Any] | None:
    """v1 fallback: highest composite-fitness alive/champion genome."""

    return await db[COLLECTION_GENOMES].find_one(
        {"status": {"$in": ["alive", "champion"]}},
        sort=[("fitness.composite", -1)],
    )


async def load_buckets(db) -> list[QueryTypeBucket]:
    """All `query_type_buckets` validated into models. Skips malformed docs."""

    buckets: list[QueryTypeBucket] = []
    async for doc in db[COLLECTION_QUERY_TYPE_BUCKETS].find({}):
        try:
            buckets.append(QueryTypeBucket.model_validate(doc))
        except Exception as exc:
            log.warning("skipping malformed query_type_bucket %s: %s", doc.get("_id"), exc)
    return buckets


async def load_latest_nash(db) -> tuple[NashStrategy | None, dict[str, Any] | None]:
    """Most recent NashStrategy snapshot. Returns (model, raw_doc) or (None, None)."""

    raw = await db[COLLECTION_NASH_STRATEGIES].find_one(sort=[("created_at", -1)])
    if raw is None:
        return None, None
    try:
        return NashStrategy.model_validate(raw), raw
    except Exception as exc:
        log.warning("latest nash_strategy malformed (%s); ignoring", exc)
        return None, None


def _empty_routing() -> dict[str, Any]:
    return {
        "bucket_key": None,
        "cosine": None,
        "nash_strategy_id": None,
        "sampled_defender_id": None,
    }


async def route_query(
    db, text: str
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Pick the defender genome for `text` and build the routing telemetry.

    See module docstring for the fallback ladder. This function never raises
    on routing-decision failures; it logs and degrades. The only None return
    for `defender_genome` is the genuine "empty population" case.
    """

    routing = _empty_routing()

    # --- Query-axis: pick the matching query-type bucket ---
    buckets = await load_buckets(db)
    query_emb: list[float] | None = None
    chosen_bucket: QueryTypeBucket | None = None
    if buckets:
        try:
            embeddings = await embed_batch([text], "voyage-4")
            query_emb = embeddings[0] if embeddings else None
        except Exception as exc:
            log.warning("query embedding failed (%s); skipping bucket routing", exc)
            query_emb = None
        if query_emb is not None:
            try:
                chosen_bucket = route_query_to_bucket(query_emb, buckets)
                routing["bucket_key"] = list(chosen_bucket.bucket_key)
                routing["cosine"] = cosine_similarity(query_emb, chosen_bucket.embedding)
            except Exception as exc:
                log.warning("bucket routing failed (%s); proceeding without bucket", exc)
                chosen_bucket = None
    else:
        log.info("no query_type_buckets seeded; bucket routing skipped")

    # --- Defender-axis: sample from the latest Nash strategy ---
    strategy, strategy_doc = await load_latest_nash(db)
    defender: dict[str, Any] | None = None
    if strategy is not None and strategy.weights:
        defender_ids = list(strategy.weights.keys())
        weights = [strategy.weights[d] for d in defender_ids]
        try:
            sampled = random.choices(defender_ids, weights=weights, k=1)[0]
        except Exception as exc:
            # random.choices raises if all weights are zero or weights/ids mismatch.
            log.warning("nash sampling failed (%s); falling back to highest-fitness", exc)
            sampled = None
        if sampled is not None:
            routing["nash_strategy_id"] = (
                strategy_doc.get("_id") if strategy_doc is not None else None
            )
            routing["sampled_defender_id"] = sampled
            defender = await db[COLLECTION_GENOMES].find_one({"_id": sampled})
            if defender is None:
                log.warning(
                    "sampled defender %s not found in genomes; falling back to highest-fitness",
                    sampled,
                )
    else:
        log.warning("no nash_strategy found (genesis state); using v1 highest-fitness defender")

    if defender is None:
        defender = await pick_highest_fitness_genome(db)

    return routing, defender
