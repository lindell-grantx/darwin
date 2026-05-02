"""HTTP service that wraps Darwin's agent evaluation pipeline.

Andrey's Hono backend (and anyone else) calls POST /evaluate with a query
text. We pick the highest-fitness alive genome, run the full agent pipeline
(Voyage retrieval → coordinator → Vertex Opus 4.6 generator → judge), persist
a fitness_evaluation, and return the full result inline.

This is the synchronous counterpart to the async query_runs queue. Use this
endpoint for live demo queries; the queue is for the evolution loop's bulk
work.

Run locally:
    MONGODB_URI=...  VOYAGE_API_KEY=...  ANTHROPIC_VERTEX_PROJECT_ID=grantx-fleet \\
        uvicorn darwin.api.server:app --host 0.0.0.0 --port 8080

Endpoints:
    GET  /health        — liveness + dependency check
    POST /evaluate      — run one (genome, query) eval, return full result
    GET  /population    — pass-through summary of alive genomes (debug)
"""

from __future__ import annotations

import logging
import os
import subprocess
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from darwin.agents.runner import run_genome
from darwin.db.client import close_client, get_db
from darwin.db.schemas import (
    COLLECTION_GENOMES,
    COLLECTION_QUERIES,
)


log = logging.getLogger("darwin.api")


# ---------------- env / startup helpers ----------------


def _resolve_secret_from_gcloud(secret: str, env_var: str) -> None:
    if os.environ.get(env_var):
        return
    try:
        value = subprocess.check_output(
            [
                "gcloud", "secrets", "versions", "access", "latest",
                f"--secret={secret}", "--project=grantx-fleet",
            ],
            text=True,
        ).strip()
        os.environ[env_var] = value
    except Exception as exc:
        log.warning("could not auto-resolve %s from gcloud secret %s: %s", env_var, secret, exc)


def _bootstrap_env() -> None:
    _resolve_secret_from_gcloud("darwin-mongodb-uri", "MONGODB_URI")
    _resolve_secret_from_gcloud("darwin-voyage-key", "VOYAGE_API_KEY")
    os.environ.setdefault("ANTHROPIC_VERTEX_PROJECT_ID", "grantx-fleet")
    os.environ.setdefault("CLOUD_ML_REGION", "global")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    _bootstrap_env()
    log.info("darwin api starting")
    # Warm the Mongo client
    await get_db()
    log.info("mongo connected")
    yield
    await close_client()
    log.info("mongo disconnected, darwin api stopped")


app = FastAPI(
    title="Darwin Evaluation API",
    description="Synchronous wrapper around the evolved-agent pipeline.",
    version="0.1.0",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- request / response shapes ----------------


class EvaluateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4_000)
    genome_id: Optional[str] = Field(
        default=None,
        description="Specific genome to evaluate against. If omitted, the highest-fitness alive (or champion) genome is used.",
    )
    persist: bool = Field(
        default=True,
        description="Whether to insert a fitness_evaluations doc. Set false for read-only / dry-run calls that won't perturb the evolution loop.",
    )


class GenomeSummary(BaseModel):
    id: str
    generation: int
    status: str
    composite_fitness: float
    retrieval_genes: dict[str, Any]
    coordination_genes: dict[str, Any]
    generation_genes: dict[str, Any]


class FitnessComponents(BaseModel):
    relevance: float
    accuracy: float
    coverage: float
    groundedness: float
    latency_ms: float
    cost_usd: float


class RetrievalTraceItem(BaseModel):
    chunk_id: str
    score: float
    position: int


class EvaluateResponse(BaseModel):
    run_id: str
    answer: str
    winning_genome: GenomeSummary
    composite_fitness: float
    fitness: FitnessComponents
    retrieval_trace: list[RetrievalTraceItem]
    rationale: Optional[str] = None
    timestamp: str


# ---------------- helpers ----------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _genome_summary(doc: dict[str, Any]) -> GenomeSummary:
    return GenomeSummary(
        id=str(doc["_id"]),
        generation=doc.get("generation", 0),
        status=doc.get("status", "unknown"),
        composite_fitness=float(doc.get("fitness", {}).get("composite", 0.0)),
        retrieval_genes=doc.get("retrieval_genes", {}),
        coordination_genes=doc.get("coordination_genes", {}),
        generation_genes=doc.get("generation_genes", {}),
    )


async def _pick_genome(db, genome_id: Optional[str]) -> dict[str, Any]:
    if genome_id is not None:
        doc = await db[COLLECTION_GENOMES].find_one({"_id": genome_id})
        if doc is None:
            raise HTTPException(status_code=404, detail=f"genome_not_found: {genome_id}")
        return doc
    doc = await db[COLLECTION_GENOMES].find_one(
        {"status": {"$in": ["alive", "champion"]}},
        sort=[("fitness.composite", -1)],
    )
    if doc is None:
        raise HTTPException(status_code=503, detail="no_alive_genomes")
    return doc


async def _upsert_query(db, text: str) -> dict[str, Any]:
    existing = await db[COLLECTION_QUERIES].find_one({"text": text})
    if existing is not None:
        return existing
    new_id = f"live-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    doc = {
        "_id": new_id,
        "text": text,
        "ground_truth": "",
        "expected_facts": ["live", "user", "submitted"],
        "difficulty": "medium",
        "domain_tags": ["live"],
        "seeded": False,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        await db[COLLECTION_QUERIES].insert_one(doc)
    except Exception:
        existing = await db[COLLECTION_QUERIES].find_one({"text": text})
        if existing is not None:
            return existing
        raise
    return doc


# ---------------- routes ----------------


@app.get("/health")
async def health():
    db = await get_db()
    try:
        await db.command("ping")
        mongo_ok = True
    except Exception as exc:
        mongo_ok = False
        log.warning("health: mongo ping failed: %s", exc)
    return {
        "ok": mongo_ok,
        "mongo": "up" if mongo_ok else "down",
        "vertex_project": os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID"),
        "vertex_region": os.environ.get("CLOUD_ML_REGION"),
        "voyage_configured": bool(os.environ.get("VOYAGE_API_KEY")),
        "timestamp": _now_iso(),
    }


@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest):
    db = await get_db()
    genome = await _pick_genome(db, req.genome_id)
    query = await _upsert_query(db, req.text)

    try:
        result = await run_genome(
            req.text,
            genome,
            ground_truth=query.get("ground_truth"),
            persist=req.persist,
        )
    except Exception as exc:
        log.exception("evaluate failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"evaluation_failed: {exc}")

    return EvaluateResponse(
        run_id=result.run_id,
        answer=result.answer,
        winning_genome=_genome_summary(genome),
        composite_fitness=result.fitness.composite,
        fitness=FitnessComponents(
            relevance=result.fitness.relevance,
            accuracy=result.fitness.accuracy,
            coverage=result.fitness.coverage,
            groundedness=result.fitness.groundedness,
            latency_ms=result.fitness.latency_ms,
            cost_usd=result.fitness.cost_usd,
        ),
        retrieval_trace=[
            RetrievalTraceItem(chunk_id=c.chunk_id, score=c.score, position=i)
            for i, c in enumerate(result.chunks, start=1)
        ],
        rationale=result.fitness.rationale,
        timestamp=_now_iso(),
    )


@app.get("/population")
async def population(limit: int = 50):
    """Debug endpoint — returns alive+champion genomes sorted by composite fitness."""

    db = await get_db()
    cursor = (
        db[COLLECTION_GENOMES]
        .find({"status": {"$in": ["alive", "champion"]}})
        .sort("fitness.composite", -1)
        .limit(max(1, min(limit, 200)))
    )
    docs = []
    async for doc in cursor:
        docs.append(_genome_summary(doc).model_dump())
    return {
        "count": len(docs),
        "genomes": docs,
        "timestamp": _now_iso(),
    }
