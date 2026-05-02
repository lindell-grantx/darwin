#!/usr/bin/env python3
"""Seed Darwin evaluation queries into MongoDB.

Usage:
    MONGO_URI="mongodb+srv://..." python scripts/seed_queries.py

The script is idempotent: it upserts by `text`, so re-running it updates the
seed content without creating duplicates.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUERIES_PATH = ROOT / "scripts" / "eval_queries.json"
DEFAULT_DATABASE = "darwin"
DEFAULT_COLLECTION = "queries"
REQUIRED_FIELDS = {
    "text",
    "ground_truth",
    "expected_facts",
    "difficulty",
    "domain_tags",
}
DIFFICULTIES = {"easy", "medium", "hard"}


def load_queries(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        queries = json.load(file)

    if not isinstance(queries, list):
        raise ValueError(f"Expected a JSON list in {path}")

    texts: set[str] = set()
    for index, query in enumerate(queries, start=1):
        if not isinstance(query, dict):
            raise ValueError(f"Query #{index} must be an object")
        missing = sorted(field for field in REQUIRED_FIELDS if field not in query)
        if missing:
            raise ValueError(f"Query #{index} is missing fields: {', '.join(missing)}")

        text = query["text"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Query #{index} has invalid `text`")
        if text in texts:
            raise ValueError(f"Duplicate query text: {text}")
        texts.add(text)

        if not isinstance(query["ground_truth"], str) or not query["ground_truth"].strip():
            raise ValueError(f"Query #{index} has invalid `ground_truth`")

        expected_facts = query["expected_facts"]
        if not isinstance(expected_facts, list) or not 3 <= len(expected_facts) <= 7:
            raise ValueError(f"Query #{index} must have 3-7 `expected_facts`")
        if not all(isinstance(fact, str) and fact.strip() for fact in expected_facts):
            raise ValueError(f"Query #{index} has invalid `expected_facts` entries")

        if query["difficulty"] not in DIFFICULTIES:
            raise ValueError(
                f"Query #{index} has invalid `difficulty`: {query['difficulty']}"
            )

        domain_tags = query["domain_tags"]
        if not isinstance(domain_tags, list) or not domain_tags:
            raise ValueError(f"Query #{index} must have non-empty `domain_tags`")
        if not all(isinstance(tag, str) and tag.strip() for tag in domain_tags):
            raise ValueError(f"Query #{index} has invalid `domain_tags` entries")

    return queries


async def seed_queries(
    mongo_uri: str,
    database_name: str,
    collection_name: str,
    queries_path: Path,
    dry_run: bool,
) -> None:
    queries = load_queries(queries_path)
    print(f"Loaded {len(queries)} queries from {queries_path}")

    if dry_run:
        for query in queries:
            tags = ", ".join(query["domain_tags"])
            print(f"- [{query['difficulty']}] {query['text']} ({tags})")
        return

    from motor.motor_asyncio import AsyncIOMotorClient

    now = datetime.now(timezone.utc)
    client = AsyncIOMotorClient(mongo_uri)
    collection = client[database_name][collection_name]

    try:
        await collection.create_index("text", unique=True)
        await collection.create_index([("difficulty", 1), ("domain_tags", 1)])
        await collection.create_index("domain_tags")

        matched = 0
        modified = 0
        upserted = 0
        for query in queries:
            document = {
                **query,
                "seeded": True,
                "updated_at": now,
            }
            result = await collection.update_one(
                {"text": query["text"]},
                {
                    "$set": document,
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )
            matched += result.matched_count
            modified += result.modified_count
            upserted += 1 if result.upserted_id is not None else 0

        print(
            "Seeded queries: "
            f"matched={matched}, "
            f"modified={modified}, "
            f"upserted={upserted}"
        )
    finally:
        client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Darwin evaluation queries")
    parser.add_argument(
        "--mongo-uri",
        default=os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI"),
        help="MongoDB connection string. Defaults to MONGO_URI or MONGODB_URI.",
    )
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES_PATH)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.mongo_uri and not args.dry_run:
        raise SystemExit(
            "Missing MongoDB URI. Set MONGO_URI/MONGODB_URI or pass --mongo-uri."
        )

    asyncio.run(
        seed_queries(
            mongo_uri=args.mongo_uri or "",
            database_name=args.database,
            collection_name=args.collection,
            queries_path=args.queries,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
