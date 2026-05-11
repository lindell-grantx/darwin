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
    MONGODB_URI=...  ANTHROPIC_VERTEX_PROJECT_ID=grantx-fleet  CLOUD_ML_REGION=global \\
        python scripts/run_query_worker.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from darwin.lib.secrets import resolve_gcp_secret  # noqa: E402

from darwin.agents.runner import evaluate as agents_evaluate  # noqa: E402
from darwin.db.client import close_client, get_db  # noqa: E402
from darwin.db.schemas import (  # noqa: E402
    COLLECTION_GENOMES,
    COLLECTION_QUERIES,
    COLLECTION_QUERY_RUNS,
)


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
    """Highest composite fitness alive/champion genome."""

    return await db[COLLECTION_GENOMES].find_one(
        {"status": {"$in": ["alive", "champion"]}},
        sort=[("fitness.composite", -1)],
    )


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
        genome = await _pick_target_genome(db)
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
            }},
        )
        log.info(
            "[run %s] completed genome=%s composite=%.3f",
            run_id[:8], genome["_id"][:8], eval_doc.get("composite_fitness", 0.0),
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
