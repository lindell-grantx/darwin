#!/usr/bin/env python3
"""Run the Python side of Darwin: query worker + evolution conductor.

Two long-lived asyncio tasks share one Mongo client:

- `darwin.evolution.conductor.watch_evaluations`: tails fitness_evaluations
  and rolls a generation when the threshold is met.
- `scripts.run_query_worker.run`: tails query_runs and processes each pending
  POST /query request.

Environment expected:
    MONGODB_URI                   (or fall through to gcloud secret darwin-mongodb-uri)
    VOYAGE_API_KEY                (or gcloud secret darwin-voyage-key)
    ANTHROPIC_VERTEX_PROJECT_ID   (default grantx-fleet)
    CLOUD_ML_REGION               (default global)

Pass --use-polling to force the conductor's polling fallback path even if
change streams are available — useful when running against a non-replica-set
Mongo (e.g. a local mongod for development).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from darwin.lib.secrets import resolve_gcp_secret  # noqa: E402

from darwin.db.client import close_client, get_db  # noqa: E402
from darwin.evolution.conductor import watch_evaluations  # noqa: E402

import run_query_worker  # noqa: E402


log = logging.getLogger("darwin.run_all")


def _resolve_mongo_uri() -> None:
    if os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI"):
        return
    uri = resolve_gcp_secret("darwin-mongodb-uri")
    if uri:
        os.environ["MONGODB_URI"] = uri


def _resolve_voyage_key() -> None:
    if os.environ.get("VOYAGE_API_KEY"):
        return
    key = resolve_gcp_secret("darwin-voyage-key")
    if key:
        os.environ["VOYAGE_API_KEY"] = key


def _set_vertex_defaults() -> None:
    os.environ.setdefault("ANTHROPIC_VERTEX_PROJECT_ID", "grantx-fleet")
    os.environ.setdefault("CLOUD_ML_REGION", "global")


async def _main(args: argparse.Namespace) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    _resolve_mongo_uri()
    _resolve_voyage_key()
    _set_vertex_defaults()

    db = await get_db()
    log.info("connected to mongo")

    stop_event = asyncio.Event()

    def _shutdown(*_a: object) -> None:
        if stop_event.is_set():
            return
        log.info("shutdown signal received")
        stop_event.set()

    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _shutdown)
        except (ValueError, OSError):
            pass

    async def _conductor_task() -> None:
        log.info("starting evolution conductor (polling=%s)", args.use_polling)
        try:
            await watch_evaluations(db, use_polling=args.use_polling)
        except asyncio.CancelledError:
            log.info("conductor cancelled")
            raise
        except Exception as exc:
            log.exception("conductor crashed: %s", exc)

    async def _worker_task() -> None:
        log.info("starting query worker")
        try:
            await run_query_worker.run(stop_event)
        except asyncio.CancelledError:
            log.info("worker cancelled")
            raise
        except Exception as exc:
            log.exception("worker crashed: %s", exc)

    conductor = asyncio.create_task(_conductor_task(), name="conductor")
    worker = asyncio.create_task(_worker_task(), name="worker")

    await stop_event.wait()
    log.info("stopping background tasks")
    conductor.cancel()
    worker.cancel()
    await asyncio.gather(conductor, worker, return_exceptions=True)
    await close_client()
    log.info("clean shutdown")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Darwin runtime supervisor.")
    p.add_argument(
        "--use-polling",
        action="store_true",
        help="Force the conductor to poll instead of using change streams.",
    )
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(_main(parse_args()))
