#!/usr/bin/env python
"""Seed the `attackers` collection with the 10 hand-curated MVP fixtures.

Idempotent: deletes existing attackers with id matching the fixture set
before re-inserting. Safe to re-run.

Usage:
    MONGODB_URI=... python scripts/seed_attackers.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

# Make src/ importable when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from darwin.attacker.fixtures import MVP_ATTACKERS
from darwin.db.client import close_client, get_db
from darwin.db.schemas import COLLECTION_ATTACKERS
from darwin.lib.secrets import resolve_gcp_secret


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("seed_attackers")


async def main() -> None:
    if not os.environ.get("MONGODB_URI"):
        uri = resolve_gcp_secret("darwin-mongodb-uri")
        if uri:
            os.environ["MONGODB_URI"] = uri

    db = await get_db()
    coll = db[COLLECTION_ATTACKERS]

    fixture_ids = [a.id for a in MVP_ATTACKERS]
    deleted = await coll.delete_many({"id": {"$in": fixture_ids}})
    log.info("deleted %d existing fixtures", deleted.deleted_count)

    docs = [a.model_dump(mode="json") for a in MVP_ATTACKERS]
    result = await coll.insert_many(docs)
    log.info("inserted %d attackers", len(result.inserted_ids))

    await close_client()


if __name__ == "__main__":
    asyncio.run(main())
