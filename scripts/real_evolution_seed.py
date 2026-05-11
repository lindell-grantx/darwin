#!/usr/bin/env python3
"""Wipe synthetic data and seed 24 real gen-0 random genomes for live evolution.

Cleanup scope:
- genomes: drop ALL (synthetic-tagged + leftovers)
- fitness_evaluations: drop ALL
- generations: drop ALL
- champions: drop ALL
- evolution_events: drop ALL
- query_runs: drop completed/failed (keep pending)

Then insert 24 fresh random_population genomes at generation=0, status=alive,
default fitness summary (composite=0).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from darwin.lib.secrets import resolve_gcp_secret  # noqa: E402

from darwin.db.client import close_client, get_db  # noqa: E402
from darwin.db.schemas import (  # noqa: E402
    COLLECTION_CHAMPIONS,
    COLLECTION_EVOLUTION_EVENTS,
    COLLECTION_FITNESS_EVALUATIONS,
    COLLECTION_GENERATIONS,
    COLLECTION_GENOMES,
    COLLECTION_QUERY_RUNS,
)
from darwin.genome.factory import random_population  # noqa: E402


log = logging.getLogger(__name__)

POP_SIZE = 24


def _resolve_uri() -> None:
    if os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI"):
        return
    uri = resolve_gcp_secret("darwin-mongodb-uri")
    if uri:
        os.environ["MONGODB_URI"] = uri


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    db = await get_db()

    pre = {
        "genomes": await db[COLLECTION_GENOMES].count_documents({}),
        "fitness_evaluations": await db[COLLECTION_FITNESS_EVALUATIONS].count_documents({}),
        "generations": await db[COLLECTION_GENERATIONS].count_documents({}),
        "champions": await db[COLLECTION_CHAMPIONS].count_documents({}),
        "evolution_events": await db[COLLECTION_EVOLUTION_EVENTS].count_documents({}),
    }
    log.info("pre-wipe counts: %s", pre)

    await db[COLLECTION_GENOMES].delete_many({})
    await db[COLLECTION_FITNESS_EVALUATIONS].delete_many({})
    await db[COLLECTION_GENERATIONS].delete_many({})
    await db[COLLECTION_CHAMPIONS].delete_many({})
    await db[COLLECTION_EVOLUTION_EVENTS].delete_many({})
    await db[COLLECTION_QUERY_RUNS].delete_many({"status": {"$in": ["completed", "failed"]}})

    log.info("wiped genomes/fitness_evaluations/generations/champions/evolution_events")

    pop = random_population(POP_SIZE, generation=0)
    docs = [g.model_dump(by_alias=True) for g in pop]
    result = await db[COLLECTION_GENOMES].insert_many(docs)
    log.info("seeded %d random gen-0 genomes", len(result.inserted_ids))

    sample = pop[0]
    log.info(
        "sample genome: id=%s gen=%d retrieval=(%s, chunk=%d, top_k=%d, rerank=%s) "
        "coordination=(%s) generation=(model=%s, reasoning=%s, critique=%s)",
        sample.id[:8],
        sample.generation,
        sample.retrieval_genes.embedding_model,
        sample.retrieval_genes.chunk_size,
        sample.retrieval_genes.top_k,
        sample.retrieval_genes.rerank,
        sample.coordination_genes.protocol,
        sample.generation_genes.model,
        sample.generation_genes.reasoning_pattern,
        sample.generation_genes.self_critique,
    )

    await close_client()


if __name__ == "__main__":
    _resolve_uri()
    asyncio.run(main())
