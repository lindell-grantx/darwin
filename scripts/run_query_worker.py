#!/usr/bin/env python3
"""Tail `query_runs` and run agent evaluations for each pending request.

Hono inserts `{status: 'pending', text: '...'}` documents. This worker:

1. Drains any `pending` rows on startup (in case a previous worker crashed
   between insert and claim).
2. Tails the change-stream for new inserts (falls back to 1 s polling if the
   change stream errors — for example on a non-replica-set deployment).
3. For each request:
   - Atomically claims it by flipping `status: pending → running`.
   - Picks the highest-fitness alive (or champion) genome as the target.
   - Upserts the request text into the `queries` collection so retrieval and
     fitness evaluation have a stable query record to work against.
   - Calls `darwin.agents.runner.evaluate(...)`, which writes the
     `fitness_evaluations` doc and gives us its `_id`.
   - Marks the request `completed` with the evaluation id + target genome id.
   - On any exception, marks `failed` with a truncated error string so Hono
     stops waiting and returns a 502.

Usage:
    MONGODB_URI=...  ANTHROPIC_VERTEX_PROJECT_ID=your-gcp-project  CLOUD_ML_REGION=global \\
        python scripts/run_query_worker.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from darwin.lib.secrets import resolve_gcp_secret  # noqa: E402

from darwin.agents.runner import evaluate as agents_evaluate  # noqa: E402
from darwin.api.routing import cosine_similarity, route_query_to_bucket  # noqa: E402
from darwin.db.client import close_client, get_db  # noqa: E402
from darwin.db.schemas import (  # noqa: E402
    COLLECTION_GENOMES,
    COLLECTION_NASH_STRATEGIES,
    COLLECTION_QUERIES,
    COLLECTION_QUERY_RUNS,
    COLLECTION_QUERY_TYPE_BUCKETS,
    NashStrategy,
    QueryTypeBucket,
)
from darwin.retrieval.embedder import embed_batch  # noqa: E402


log = logging.getLogger("query_worker")

POLL_INTERVAL_SEC = 1.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_mongo_uri() -> None:
    if os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI"):
        return
    uri = resolve_gcp_secret("darwin-mongodb-uri")
    if uri:
        os.environ["MONGODB_URI"] = uri


class _MinimalBlackboard:
    """Adapter so `agents.runner.evaluate` can call `snapshot_for(genome_id)`."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id

    def snapshot_for(self, genome_id: str) -> dict[str, Any]:
        return {"run_id": self.run_id, "source": "live-query"}


async def _claim(db, run_id: str) -> dict[str, Any] | None:
    """Atomically flip pending → running. Returns the doc, or None if someone else got it."""

    return await db[COLLECTION_QUERY_RUNS].find_one_and_update(
        {"_id": run_id, "status": "pending"},
        {"$set": {"status": "running", "started_at": _now()}},
        return_document=True,
    )


async def _pick_target_genome(db) -> dict[str, Any] | None:
    """Highest composite fitness alive/champion genome (v1 fallback path)."""

    return await db[COLLECTION_GENOMES].find_one(
        {"status": {"$in": ["alive", "champion"]}},
        sort=[("fitness.composite", -1)],
    )


async def _load_buckets(db) -> list[QueryTypeBucket]:
    """Load all QueryTypeBucket docs as validated models. Empty list if none seeded."""

    buckets: list[QueryTypeBucket] = []
    async for doc in db[COLLECTION_QUERY_TYPE_BUCKETS].find({}):
        try:
            buckets.append(QueryTypeBucket.model_validate(doc))
        except Exception as exc:
            log.warning("skipping malformed query_type_bucket %s: %s", doc.get("_id"), exc)
    return buckets


async def _load_latest_nash(db) -> tuple[NashStrategy | None, dict[str, Any] | None]:
    """Most recent NashStrategy snapshot. Returns (model, raw_doc) or (None, None)."""

    raw = await db[COLLECTION_NASH_STRATEGIES].find_one(sort=[("created_at", -1)])
    if raw is None:
        return None, None
    try:
        return NashStrategy.model_validate(raw), raw
    except Exception as exc:
        log.warning("latest nash_strategy malformed (%s); ignoring", exc)
        return None, None


async def _route_query(
    db, text: str
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Pick the defender genome for this query and build the routing telemetry.

    Returns (routing_doc, defender_genome). The routing_doc is always shaped
    like the schema described in Task 13 (with nulls where the inputs aren't
    available); the defender_genome is None only when no usable genome exists
    at all (caller must surface that as a failure).

    Fallback ladder:
      - If buckets seeded: embed the query, pick best-cosine bucket.
      - If a NashStrategy exists: sample defender id by weight; look up the
        genome doc. If lookup fails, fall back to highest-fitness alive.
      - If no Nash strategy: log a warning and use the v1 highest-fitness path.
    """

    routing: dict[str, Any] = {
        "bucket_key": None,
        "cosine": None,
        "nash_strategy_id": None,
        "sampled_defender_id": None,
    }

    # --- Query-axis routing: find the matching query-type bucket ---
    buckets = await _load_buckets(db)
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

    # --- Defender-axis routing: sample from the latest Nash strategy ---
    strategy, strategy_doc = await _load_latest_nash(db)
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
        defender = await _pick_target_genome(db)

    return routing, defender


async def _upsert_query(db, text: str) -> dict[str, Any]:
    """Find or create a `queries` row keyed by text. Live queries get minimal metadata."""

    existing = await db[COLLECTION_QUERIES].find_one({"text": text})
    if existing is not None:
        return existing
    new_id = f"live-{int(_now().timestamp() * 1000)}"
    doc = {
        "_id": new_id,
        "text": text,
        "ground_truth": "",
        "expected_facts": ["live", "user", "submitted"],
        "difficulty": "medium",
        "domain_tags": ["live"],
        "seeded": False,
        "created_at": _now(),
    }
    try:
        await db[COLLECTION_QUERIES].insert_one(doc)
    except Exception:
        # Another worker raced us — fetch the winning version.
        existing = await db[COLLECTION_QUERIES].find_one({"text": text})
        if existing is not None:
            return existing
        raise
    return doc


async def _process(db, run_doc: dict[str, Any]) -> None:
    run_id = run_doc["_id"]
    text = run_doc.get("text", "").strip()
    if not text:
        await db[COLLECTION_QUERY_RUNS].update_one(
            {"_id": run_id},
            {"$set": {"status": "failed", "completed_at": _now(), "error": "empty text"}},
        )
        return

    log.info("[run %s] processing %r", run_id[:8], text[:60])

    claimed = await _claim(db, run_id)
    if claimed is None:
        log.info("[run %s] already claimed by another worker; skipping", run_id[:8])
        return

    try:
        routing, genome = await _route_query(db, text)
        if genome is None:
            raise RuntimeError("no alive genomes available")
        query = await _upsert_query(db, text)
        eval_doc = await agents_evaluate(
            genome,
            query,
            run_id=run_id,
            blackboard=_MinimalBlackboard(run_id),
        )
        await db[COLLECTION_QUERY_RUNS].update_one(
            {"_id": run_id},
            {"$set": {
                "status": "completed",
                "completed_at": _now(),
                "target_genome_id": str(genome["_id"]),
                # eval_doc["_id"] may be an ObjectId (Mongo-generated) or str — normalise.
                "evaluation_id": str(eval_doc.get("_id")) if eval_doc.get("_id") is not None else None,
                "routing": routing,
            }},
        )
        log.info(
            "[run %s] completed genome=%s composite=%.3f bucket=%s nash=%s sampled=%s",
            run_id[:8],
            str(genome["_id"])[:8],
            eval_doc.get("composite_fitness", 0.0),
            routing.get("bucket_key"),
            (routing.get("nash_strategy_id") or "")[:8] if routing.get("nash_strategy_id") else None,
            (routing.get("sampled_defender_id") or "")[:8] if routing.get("sampled_defender_id") else None,
        )
    except Exception as exc:
        log.exception("[run %s] failed: %s", run_id[:8], exc)
        await db[COLLECTION_QUERY_RUNS].update_one(
            {"_id": run_id},
            {"$set": {
                "status": "failed",
                "completed_at": _now(),
                "error": str(exc)[:500],
            }},
        )


async def _drain_pending(db) -> int:
    """On startup: process any runs that were pending when the worker died."""

    count = 0
    async for run in db[COLLECTION_QUERY_RUNS].find({"status": "pending"}):
        await _process(db, run)
        count += 1
    if count:
        log.info("drained %d pending run(s) from before startup", count)
    return count


async def _watch_change_stream(db, stop_event: asyncio.Event) -> bool:
    """Returns True if the change stream worked at least once, False if it errored out."""

    log.info("subscribing to query_runs change stream (operationType=insert)")
    try:
        async with db[COLLECTION_QUERY_RUNS].watch(
            [{"$match": {"operationType": "insert"}}],
            full_document="updateLookup",
        ) as stream:
            while not stop_event.is_set():
                try:
                    change = await asyncio.wait_for(stream.next(), timeout=2.0)
                except asyncio.TimeoutError:
                    continue
                doc = change.get("fullDocument")
                if not doc:
                    continue
                if doc.get("status") != "pending":
                    continue
                await _process(db, doc)
            return True
    except Exception as exc:
        log.warning("change stream error (%s); falling back to polling", exc)
        return False


async def _poll_loop(db, stop_event: asyncio.Event) -> None:
    log.info("polling query_runs every %.1fs (change stream unavailable)", POLL_INTERVAL_SEC)
    while not stop_event.is_set():
        try:
            async for run in db[COLLECTION_QUERY_RUNS].find({"status": "pending"}):
                if stop_event.is_set():
                    break
                await _process(db, run)
        except Exception as exc:
            log.exception("poll iteration failed: %s", exc)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=POLL_INTERVAL_SEC)
        except asyncio.TimeoutError:
            pass


async def run(stop_event: asyncio.Event | None = None) -> None:
    if stop_event is None:
        stop_event = asyncio.Event()

    _resolve_mongo_uri()
    db = await get_db()

    await _drain_pending(db)

    # Try change stream; on failure, fall back to polling. Loop the change-stream
    # path so transient errors don't permanently demote us to polling.
    while not stop_event.is_set():
        ok = await _watch_change_stream(db, stop_event)
        if stop_event.is_set():
            break
        if not ok:
            await _poll_loop(db, stop_event)
            break  # polling runs until stop


def _install_signal_handlers(stop_event: asyncio.Event) -> None:
    def _handler(*_a: Any) -> None:
        log.info("received signal; shutting down")
        stop_event.set()
    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _handler)
        except (ValueError, OSError):
            # Not all signals are available on Windows.
            pass


async def _main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    stop_event = asyncio.Event()
    _install_signal_handlers(stop_event)
    try:
        await run(stop_event)
    finally:
        await close_client()


if __name__ == "__main__":
    asyncio.run(_main())
