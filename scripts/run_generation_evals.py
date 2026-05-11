#!/usr/bin/env python3
"""Fire 120 evals (24 genomes x 5 queries) against the live /evaluate endpoint.

Drives one generation's evaluation phase. The conductor (running as
darwin-evolution.service on the VM) watches fitness_evaluations via change
stream and auto-rolls to the next generation when the threshold is met.

Usage:
    EVAL_API=http://localhost:8080 python scripts/run_generation_evals.py
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from darwin.lib.secrets import resolve_gcp_secret  # noqa: E402

from darwin.db.client import close_client, get_db  # noqa: E402
from darwin.db.schemas import COLLECTION_FITNESS_EVALUATIONS, COLLECTION_GENOMES, COLLECTION_QUERIES  # noqa: E402


log = logging.getLogger(__name__)


DEFAULT_API = "http://localhost:8080"
QUERIES_PER_GENOME = 5
CONCURRENCY = 6
PER_CALL_TIMEOUT_SEC = 90.0


def _resolve_uri() -> None:
    if os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI"):
        return
    uri = resolve_gcp_secret("darwin-mongodb-uri")
    if uri:
        os.environ["MONGODB_URI"] = uri


async def _pick_queries(db, n: int) -> list[dict[str, Any]]:
    """Pick a varied subset: spread across difficulties + domains."""
    all_queries = []
    async for q in db[COLLECTION_QUERIES].find({"seeded": True}).limit(200):
        all_queries.append(q)
    if len(all_queries) <= n:
        return all_queries

    # Strategy: pick by difficulty buckets (easy/medium/hard)
    buckets: dict[str, list] = {"easy": [], "medium": [], "hard": []}
    for q in all_queries:
        buckets.setdefault(q.get("difficulty", "medium"), []).append(q)

    picked: list[dict] = []
    # Round-robin one per bucket until we hit n
    bucket_iters = {k: iter(v) for k, v in buckets.items() if v}
    while len(picked) < n and bucket_iters:
        for k in list(bucket_iters):
            try:
                picked.append(next(bucket_iters[k]))
                if len(picked) >= n:
                    break
            except StopIteration:
                bucket_iters.pop(k, None)
    return picked[:n]


async def _fetch_alive_genomes(db) -> list[dict[str, Any]]:
    cursor = db[COLLECTION_GENOMES].find({"status": "alive"}).sort("generation", -1)
    out = []
    async for g in cursor:
        out.append(g)
    return out


async def _evaluate_one(
    client: httpx.AsyncClient,
    api: str,
    genome_id: str,
    query_text: str,
    sem: asyncio.Semaphore,
    counter: list[int],
    total: int,
    start_time: float,
) -> dict[str, Any]:
    async with sem:
        idx = counter[0]
        counter[0] += 1
        t0 = time.perf_counter()
        try:
            r = await client.post(
                f"{api}/evaluate",
                json={"text": query_text, "genome_id": genome_id, "persist": True},
                timeout=PER_CALL_TIMEOUT_SEC,
            )
            dt = time.perf_counter() - t0
            if r.status_code != 200:
                elapsed = time.perf_counter() - start_time
                log.warning("[%d/%d %.0fs] HTTP %d for genome=%s — %s",
                            idx + 1, total, elapsed, r.status_code, genome_id[:8], r.text[:200])
                return {"genome_id": genome_id, "ok": False, "status": r.status_code}
            data = r.json()
            elapsed = time.perf_counter() - start_time
            log.info("[%d/%d %.0fs] genome=%s composite=%.3f (%.1fs)",
                     idx + 1, total, elapsed, genome_id[:8], data["composite_fitness"], dt)
            return {"genome_id": genome_id, "ok": True, "composite": data["composite_fitness"], "elapsed_sec": dt}
        except Exception as exc:
            elapsed = time.perf_counter() - start_time
            log.warning("[%d/%d %.0fs] EXC for genome=%s: %s",
                        idx + 1, total, elapsed, genome_id[:8], str(exc)[:200])
            return {"genome_id": genome_id, "ok": False, "error": str(exc)[:200]}


async def main(args: argparse.Namespace) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    api = os.environ.get("EVAL_API", DEFAULT_API).rstrip("/")
    log.info("using API %s", api)

    db = await get_db()
    genomes = await _fetch_alive_genomes(db)
    if not genomes:
        log.error("no alive genomes — seed gen-0 first")
        return
    current_gen = genomes[0]["generation"]
    log.info("found %d alive genomes (current generation: %d)", len(genomes), current_gen)

    queries = await _pick_queries(db, QUERIES_PER_GENOME)
    log.info("picked %d queries: %s", len(queries),
             [(q["difficulty"], q["text"][:50] + "...") for q in queries])

    pre_evals = await db[COLLECTION_FITNESS_EVALUATIONS].count_documents({"generation": current_gen})
    log.info("pre-batch fitness_evaluations for gen %d: %d", current_gen, pre_evals)

    pairs = [(g["_id"], q["text"]) for g in genomes for q in queries]
    total = len(pairs)
    log.info("dispatching %d (genome, query) evaluations at concurrency %d", total, CONCURRENCY)

    sem = asyncio.Semaphore(CONCURRENCY)
    counter = [0]
    start = time.perf_counter()

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[
            _evaluate_one(client, api, gid, qt, sem, counter, total, start)
            for gid, qt in pairs
        ])

    ok_count = sum(1 for r in results if r["ok"])
    composites = [r["composite"] for r in results if r.get("ok")]
    elapsed = time.perf_counter() - start
    log.info("=" * 60)
    log.info("BATCH COMPLETE: %d/%d ok in %.1fs (avg %.1fs/eval)",
             ok_count, total, elapsed, elapsed / max(1, total))
    if composites:
        log.info("composite stats: min=%.3f mean=%.3f max=%.3f",
                 min(composites), sum(composites) / len(composites), max(composites))

    post_evals = await db[COLLECTION_FITNESS_EVALUATIONS].count_documents({"generation": current_gen})
    log.info("post-batch fitness_evaluations for gen %d: %d (delta=%d)",
             current_gen, post_evals, post_evals - pre_evals)

    await close_client()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run one generation worth of /evaluate calls.")
    return p.parse_args()


if __name__ == "__main__":
    _resolve_uri()
    asyncio.run(main(parse_args()))
