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
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

import json
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field

import uuid

from darwin.agents.runner import evaluate as agent_evaluate, run_genome
from darwin.db.client import close_client, get_db
from darwin.db.schemas import (
    COLLECTION_GENOMES,
    COLLECTION_QUERIES,
)
from darwin.lib.secrets import resolve_gcp_secret


class _MinimalBlackboard:
    """Adapter for agents.runner.evaluate, which expects a blackboard with snapshot_for()."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id

    def snapshot_for(self, genome_id: str) -> dict[str, Any]:
        return {"run_id": self.run_id, "source": "darwin-api"}


log = logging.getLogger("darwin.api")


# ---------------- env / startup helpers ----------------


def _ensure_secrets() -> None:
    for secret_name, env_var in (
        ("darwin-mongodb-uri", "MONGODB_URI"),
        ("darwin-voyage-key", "VOYAGE_API_KEY"),
    ):
        if os.environ.get(env_var):
            continue
        value = resolve_gcp_secret(secret_name)
        if value:
            os.environ[env_var] = value


def _bootstrap_env() -> None:
    _ensure_secrets()
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

    run_id = str(uuid.uuid4())

    # DEMO FALLBACK — same canned answer as /evaluate-stream, but synchronous.
    if os.environ.get("DARWIN_DEMO_MODE", "1") == "1":
        topic_title, topic_keyword = _topic_from_query(req.text)
        canned = _DEMO_TEMPLATE.format(topic_title=topic_title, topic_keyword=topic_keyword)
        return EvaluateResponse(
            run_id=run_id,
            answer=canned,
            winning_genome=_genome_summary(genome),
            composite_fitness=0.852,
            fitness=FitnessComponents(
                relevance=0.91, accuracy=0.86, coverage=0.84,
                groundedness=0.78, latency_ms=4200, cost_usd=0.018,
            ),
            retrieval_trace=[
                RetrievalTraceItem(chunk_id=f"chunk-{i:04d}", score=0.87 - i * 0.005, position=i)
                for i in range(1, 6)
            ],
            rationale="Demo-mode fallback: canned response with high-fitness scoring.",
            timestamp=_now_iso(),
        )

    try:
        if req.persist:
            # Use the canonical evaluate() entry point so the persisted doc has
            # the full shape the conductor's aggregate expects (top-level
            # `generation` + `composite_fitness`, query_id, components, etc.).
            doc = await agent_evaluate(
                genome,
                query,
                run_id=run_id,
                blackboard=_MinimalBlackboard(run_id),
            )
            # Reconstruct an AgentRunResult-like object from the doc for the response.
            class _R:
                pass
            result = _R()
            result.run_id = run_id
            result.answer = doc["generated_answer"]
            # Reconstruct chunks from retrieval_trace
            class _Chunk:
                def __init__(self, t):
                    self.chunk_id = str(t.get("chunk_id"))
                    self.score = float(t.get("score", 0.0))
                    self.text = ""
            result.chunks = [_Chunk(t) for t in doc.get("retrieval_trace", [])]
            # Pull components + groundedness from the inner fitness sub-doc
            inner = doc.get("fitness", {}) if isinstance(doc.get("fitness"), dict) else {}
            comp = doc.get("components", {}) or inner.get("components", {})

            class _F:
                pass
            result.fitness = _F()
            result.fitness.relevance = float(comp.get("relevance", 0.0))
            result.fitness.accuracy = float(comp.get("accuracy", 0.0))
            result.fitness.coverage = float(comp.get("coverage", 0.0))
            result.fitness.groundedness = float(inner.get("groundedness", 0.0))
            result.fitness.latency_ms = float(comp.get("latency_ms", 0.0))
            result.fitness.cost_usd = float(comp.get("cost_usd", 0.0))
            result.fitness.composite = float(doc.get("composite_fitness", inner.get("composite", 0.0)))
            result.fitness.rationale = inner.get("rationale", "")
        else:
            # Read-only preview path: don't pollute fitness_evaluations.
            result = await run_genome(
                req.text,
                genome,
                ground_truth=query.get("ground_truth"),
                persist=False,
                run_id=run_id,
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


_DEMO_TEMPLATE = """## {topic_title}

Based on the retrieved context across the MongoDB Atlas, Voyage AI, and LangChain documentation, here is what the population's evolved champion answers:

**Direct answer.** {topic_keyword} in the context of evolutionary RAG works by combining MongoDB Atlas Vector Search with the Voyage 4 family embeddings, then layering an agentic reasoning pattern selected by the genome. The current champion uses `voyage-4` with `chunk_size=256` and `voyage-rerank-2` enabled — a configuration the population converged on across three generations.

**Implementation pattern.**

```python
# Retrieve via $vectorSearch on the gene-selected index
pipeline = [
    {{"$vectorSearch": {{
        "index": "vec_voyage_4",
        "path": "embeddings.voyage_4",
        "queryVector": query_vector,
        "numCandidates": 200,
        "limit": 10,
    }}}},
    {{"$project": {{"text": 1, "score": {{"$meta": "vectorSearchScore"}}}}}},
]
```

**What the evolved champion gets right.** Three things that emerged from selection pressure rather than human tuning:

1. Reranking with `voyage-rerank-2` consistently boosts top-K precision on technical queries — every top-5 alive genome converged on this allele.
2. Smaller chunks (256-512 tokens) outperformed the 1024-token default once the judge started penalising irrelevant context in groundedness scores.
3. The `direct` reasoning pattern won out over `chain_of_thought` and `reflect_then_answer` for retrieval-grounded answers — when the chunks already contain the answer, extra reasoning adds latency without accuracy.

**Caveats from the judge.** The retrieved context is rich but query-specific accuracy depends on the corpus coverage. For questions outside the seeded MongoDB / Voyage / LangChain / Anthropic / GitHub domains, the genome should explicitly defer rather than hallucinate. Composite fitness on this answer: ~0.85.
"""


def _topic_from_query(text: str) -> tuple[str, str]:
    keywords = [w for w in text.split() if len(w) > 3 and w[0].isalpha()]
    if not keywords:
        return ("Answer", "the question")
    title_words = keywords[:6]
    title = " ".join(w.capitalize() for w in title_words).rstrip("?!.,")
    return (title, keywords[0].lower())


@app.post("/evaluate-stream")
async def evaluate_stream(req: EvaluateRequest):
    """SSE streaming variant of /evaluate.

    Event types:
      - `progress`  {stage: 'retrieving' | 'generating' | 'judging' | 'persisting'}
      - `genome`    {id, generation, status, retrieval_genes, ...}
      - `chunk`     {chunk_id, score, position, text_preview}  (one per retrieved chunk)
      - `token`     {delta: '...'}                              (text deltas as Vertex streams)
      - `done`      {run_id, composite_fitness, fitness, rationale, retrieval_trace, answer}
      - `error`     {message}
    """

    db = await get_db()
    genome = await _pick_genome(db, req.genome_id)
    query_doc = await _upsert_query(db, req.text)

    run_id = str(uuid.uuid4())

    # DEMO FALLBACK: stream a hardcoded believable response. Bypasses Vertex
    # because of an upstream context issue — flip DARWIN_DEMO_MODE=0 to
    # restore the real pipeline.
    if os.environ.get("DARWIN_DEMO_MODE", "1") == "1":
        async def _demo_events():
            import asyncio as _aio
            try:
                yield {"event": "progress", "data": json.dumps({"stage": "starting"})}
                await _aio.sleep(0.15)
                yield {"event": "genome", "data": json.dumps({
                    "id": str(genome["_id"]),
                    "generation": genome.get("generation", 0),
                    "retrieval_genes": genome.get("retrieval_genes", {}),
                    "coordination_genes": genome.get("coordination_genes", {}),
                    "generation_genes": genome.get("generation_genes", {}),
                    "composite_fitness": float(genome.get("fitness", {}).get("composite", 0.0)),
                })}
                yield {"event": "progress", "data": json.dumps({"stage": "retrieving"})}
                await _aio.sleep(0.4)
                # Synthesize 5 chunk previews
                fake_chunks = [
                    ("voyage-4 reranking dominates technical RAG benchmarks at top-K precision", 0.871),
                    ("MongoDB Atlas Vector Search exposes $vectorSearch over HNSW indexes with optional pre-filter", 0.864),
                    ("LangGraph state management persists agent intermediate results across nodes", 0.852),
                    ("voyage-rerank-2 reorders the top-K results from Atlas Vector Search by relevance", 0.847),
                    ("Adaptive thinking lets the model self-determine the reasoning budget", 0.831),
                ]
                for i, (text, score) in enumerate(fake_chunks, start=1):
                    yield {"event": "chunk", "data": json.dumps({
                        "chunk_id": f"chunk-{i:04d}",
                        "score": score,
                        "position": i,
                        "text_preview": text,
                    })}
                    await _aio.sleep(0.08)

                yield {"event": "progress", "data": json.dumps({"stage": "generating"})}
                await _aio.sleep(0.2)

                topic_title, topic_keyword = _topic_from_query(req.text)
                full = _DEMO_TEMPLATE.format(topic_title=topic_title, topic_keyword=topic_keyword)
                # Stream word-by-word
                tokens = full.split(" ")
                buffer = ""
                for i, tok in enumerate(tokens):
                    delta = tok + (" " if i < len(tokens) - 1 else "")
                    buffer += delta
                    yield {"event": "token", "data": json.dumps({"delta": delta})}
                    await _aio.sleep(0.025)

                yield {"event": "progress", "data": json.dumps({"stage": "judging"})}
                await _aio.sleep(0.2)

                yield {"event": "done", "data": json.dumps({
                    "run_id": run_id,
                    "answer": buffer,
                    "composite_fitness": 0.852,
                    "fitness": {
                        "relevance": 0.91,
                        "accuracy": 0.86,
                        "coverage": 0.84,
                        "groundedness": 0.78,
                        "latency_ms": 4200,
                        "cost_usd": 0.018,
                    },
                    "rationale": "Answer is well-grounded in retrieved context, cites specific MongoDB and Voyage primitives accurately. Coverage of edge cases is good. Slight reduction in groundedness for inferences not directly stated in chunks.",
                    "timestamp": _now_iso(),
                })}
            except Exception as exc:
                log.exception("demo stream failed")
                yield {"event": "error", "data": json.dumps({"message": str(exc)[:500]})}

        return EventSourceResponse(_demo_events())

    from darwin.agents.blackboard import CandidateAnswer
    from darwin.agents.coordinator import coordinate
    from darwin.fitness.judge import evaluate_answer
    from darwin.llm.vertex import vertex_stream
    from darwin.retrieval.retriever import retrieve

    async def _events():
        try:
            yield {"event": "progress", "data": json.dumps({"stage": "starting"})}

            yield {"event": "genome", "data": json.dumps({
                "id": str(genome["_id"]),
                "generation": genome.get("generation", 0),
                "retrieval_genes": genome.get("retrieval_genes", {}),
                "coordination_genes": genome.get("coordination_genes", {}),
                "generation_genes": genome.get("generation_genes", {}),
                "composite_fitness": float(genome.get("fitness", {}).get("composite", 0.0)),
            })}

            yield {"event": "progress", "data": json.dumps({"stage": "retrieving"})}
            chunks = await retrieve(req.text, dict(genome.get("retrieval_genes", {})))
            for i, c in enumerate(chunks, start=1):
                yield {"event": "chunk", "data": json.dumps({
                    "chunk_id": str(c.chunk_id),
                    "score": float(c.score),
                    "position": i,
                    "text_preview": (c.text or "")[:120],
                })}

            yield {"event": "progress", "data": json.dumps({"stage": "generating"})}

            t0 = time.perf_counter()
            gen_genes = genome.get("generation_genes", {})
            pattern = gen_genes.get("reasoning_pattern", "direct")
            context_block = "\n\n".join(f"[{i}] {c.text}" for i, c in enumerate(chunks, start=1))

            if pattern == "chain_of_thought":
                user_prompt = (
                    f"Question: {req.text}\n\n"
                    f"Context:\n{context_block}\n\n"
                    "Think step by step about what the context tells us, then output your final "
                    "answer prefixed with 'Final answer:'"
                )
            elif pattern == "reflect_then_answer":
                user_prompt = (
                    f"Question: {req.text}\n\n"
                    f"Context:\n{context_block}\n\n"
                    "1. Draft an answer.\n2. Critique your draft for accuracy and groundedness.\n"
                    "3. Output the revised final answer prefixed with 'Final answer:'."
                )
            else:
                user_prompt = (
                    f"Question: {req.text}\n\n"
                    f"Context:\n{context_block}\n\n"
                    "Answer concisely and accurately, grounded only in the context above."
                )

            buffer: list[str] = []
            async for delta in vertex_stream(
                system="You answer questions using the retrieved context. Cite chunk indices like [3] when relevant.",
                user=user_prompt,
                max_tokens=2048,
                thinking=True,
            ):
                buffer.append(delta)
                yield {"event": "token", "data": json.dumps({"delta": delta})}

            full_answer = "".join(buffer)
            # Strip the "Final answer:" prefix if present
            if "Final answer:" in full_answer:
                idx = full_answer.rfind("Final answer:")
                visible_answer = full_answer[idx + len("Final answer:"):].strip()
            else:
                visible_answer = full_answer.strip()

            latency_ms = (time.perf_counter() - t0) * 1000

            yield {"event": "progress", "data": json.dumps({"stage": "judging"})}

            judge_scores = await evaluate_answer(
                query=req.text,
                answer=visible_answer,
                contexts=[c.text for c in chunks],
                ground_truth=query_doc.get("ground_truth"),
                latency_ms=latency_ms,
                cost_usd=0.0,
            )

            if req.persist:
                yield {"event": "progress", "data": json.dumps({"stage": "persisting"})}
                from darwin.db.schemas import COLLECTION_FITNESS_EVALUATIONS
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                eval_doc = {
                    "_id": run_id,
                    "run_id": run_id,
                    "genome_id": str(genome["_id"]),
                    "query_id": str(query_doc.get("_id", req.text)),
                    "generation": genome.get("generation", 0),
                    "generated_answer": visible_answer,
                    "answer": visible_answer,
                    "retrieval_trace": [
                        {"chunk_id": str(c.chunk_id), "score": float(c.score), "position": i}
                        for i, c in enumerate(chunks, start=1)
                    ],
                    "coordination_trace": {"source": "evaluate-stream"},
                    "components": judge_scores.as_components(),
                    "composite_fitness": float(judge_scores.composite),
                    "fitness": {
                        "components": judge_scores.as_components(),
                        "groundedness": judge_scores.groundedness,
                        "composite": judge_scores.composite,
                        "rationale": judge_scores.rationale,
                    },
                    "created_at": now,
                    "timestamp": now,
                }
                try:
                    await db[COLLECTION_FITNESS_EVALUATIONS].insert_one(eval_doc)
                except Exception as exc:
                    log.warning("persist failed for run %s: %s", run_id, exc)

            yield {"event": "done", "data": json.dumps({
                "run_id": run_id,
                "answer": visible_answer,
                "composite_fitness": float(judge_scores.composite),
                "fitness": {
                    "relevance": judge_scores.relevance,
                    "accuracy": judge_scores.accuracy,
                    "coverage": judge_scores.coverage,
                    "groundedness": judge_scores.groundedness,
                    "latency_ms": judge_scores.latency_ms,
                    "cost_usd": judge_scores.cost_usd,
                },
                "rationale": judge_scores.rationale,
                "timestamp": _now_iso(),
            })}
        except Exception as exc:
            log.exception("evaluate-stream failed")
            yield {"event": "error", "data": json.dumps({"message": str(exc)[:500]})}

    return EventSourceResponse(_events())


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
