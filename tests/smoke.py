"""Smoke checks for the Darwin demo path.

Run with:
    pytest tests/smoke.py -v

The suite is staged so it is useful before the full stack exists:
- Local artifact checks always run.
- MongoDB checks run only when MONGODB_URI or MONGO_URI is set.
- API checks run only when DARWIN_API_URL is set.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from urllib import request

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVAL_QUERIES_PATH = ROOT / "scripts" / "eval_queries.json"

REQUIRED_COLLECTIONS = {
    "chunks",
    "genomes",
    "queries",
    "fitness_evaluations",
    "generations",
    "champions",
}

MIN_QUERY_COUNT = 25
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_eval_queries_structure() -> None:
    """Eval queries are the seeded input to the demo loop. Validate file shape."""
    assert EVAL_QUERIES_PATH.exists(), f"Missing {EVAL_QUERIES_PATH}"

    queries = _load_json(EVAL_QUERIES_PATH)
    assert isinstance(queries, list)
    assert len(queries) >= MIN_QUERY_COUNT

    seen_texts: set[str] = set()

    for index, query in enumerate(queries, start=1):
        assert isinstance(query, dict), f"Query #{index} must be an object"
        assert isinstance(query.get("text"), str) and query["text"].strip()
        assert query["text"] not in seen_texts
        seen_texts.add(query["text"])

        assert isinstance(query.get("ground_truth"), str)
        assert query["ground_truth"].strip()

        expected_facts = query.get("expected_facts")
        assert isinstance(expected_facts, list)
        assert 3 <= len(expected_facts) <= 7
        assert all(isinstance(fact, str) and fact.strip() for fact in expected_facts)

        assert query.get("difficulty") in ALLOWED_DIFFICULTIES

        domain_tags = query.get("domain_tags")
        assert isinstance(domain_tags, list) and domain_tags
        assert all(isinstance(tag, str) and tag.strip() for tag in domain_tags)


def test_mongodb_seed_state_if_configured() -> None:
    """When Atlas is configured, verify the collections needed for the demo."""
    mongo_uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI")
    if not mongo_uri:
        pytest.skip("Set MONGODB_URI or MONGO_URI to run MongoDB smoke checks")

    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ModuleNotFoundError:
        pytest.skip("Install motor to run MongoDB smoke checks")

    db_name = os.environ.get("DB_NAME", "darwin")

    async def check_database() -> None:
        client = AsyncIOMotorClient(mongo_uri)
        try:
            db = client[db_name]
            collection_names = set(await db.list_collection_names())
            missing = REQUIRED_COLLECTIONS - collection_names
            assert not missing, f"Missing collections: {sorted(missing)}"

            query_count = await db.queries.count_documents({})
            assert query_count >= 25

            chunk = await db.chunks.find_one({})
            assert chunk is not None, "Expected at least one seeded chunk"
            embeddings = chunk.get("embeddings", {})
            assert isinstance(embeddings, dict) and embeddings
        finally:
            client.close()

    asyncio.run(check_database())


def test_api_happy_path_if_configured() -> None:
    """When the backend is running, verify the public demo endpoints respond."""
    base_url = os.environ.get("DARWIN_API_URL")
    if not base_url:
        pytest.skip("Set DARWIN_API_URL to run API smoke checks")

    base_url = base_url.rstrip("/")

    for endpoint in ("/population", "/fitness-curve", "/champions"):
        with request.urlopen(f"{base_url}{endpoint}", timeout=10) as response:
            assert response.status == 200
            payload = json.loads(response.read().decode("utf-8"))
            assert isinstance(payload, dict)

    query_payload = json.dumps(
        {"text": "How do I create an Atlas Vector Search index?"}
    ).encode("utf-8")
    req = request.Request(
        f"{base_url}/query",
        data=query_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=30) as response:
        assert response.status == 200
        payload = json.loads(response.read().decode("utf-8"))

    assert payload.get("answer")
    assert payload.get("winning_genome")
    assert payload.get("fitness")
