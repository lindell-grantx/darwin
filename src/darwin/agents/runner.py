"""End-to-end genome run: retrieve, answer, judge, and persist trace."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from darwin.agents.blackboard import CandidateAnswer
from darwin.agents.coordinator import coordinate
from darwin.fitness.judge import JudgeScores, evaluate_answer
from darwin.retrieval.retriever import RetrievedChunk, retrieve


@dataclass(frozen=True)
class AgentRunResult:
    run_id: str
    genome_id: str
    answer: str
    chunks: list[RetrievedChunk]
    candidates: list[CandidateAnswer]
    fitness: JudgeScores

    def to_document(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "genome_id": self.genome_id,
            "answer": self.answer,
            "retrieval_trace": [
                {"chunk_id": chunk.chunk_id, "score": chunk.score, "position": index}
                for index, chunk in enumerate(self.chunks, start=1)
            ],
            "agents": [
                {
                    "name": candidate.agent_name,
                    "confidence": candidate.confidence,
                    "answer": candidate.answer,
                    "notes": candidate.notes,
                }
                for candidate in self.candidates
            ],
            "fitness": {
                "components": self.fitness.as_components(),
                "coverage": self.fitness.coverage,
                "groundedness": self.fitness.groundedness,
                "composite": self.fitness.composite,
                "rationale": self.fitness.rationale,
            },
            "created_at": datetime.now(timezone.utc),
        }


async def run_genome(
    query: str,
    genome: dict[str, Any],
    ground_truth: str | None = None,
    persist: bool = True,
    run_id: str | None = None,
) -> AgentRunResult:
    started = time.perf_counter()
    genome_id = str(genome.get("_id") or genome.get("id") or "unknown-genome")
    retrieval_genes = dict(genome.get("retrieval_genes", {}))
    coordination_genes = dict(genome.get("coordination_genes", {}))

    chunks = await retrieve(query, retrieval_genes)
    answer, candidates = await coordinate(query, chunks, coordination_genes, genome=genome)
    latency_ms = (time.perf_counter() - started) * 1000
    fitness = await evaluate_answer(
        query=query,
        answer=answer,
        contexts=[chunk.text for chunk in chunks],
        ground_truth=ground_truth,
        latency_ms=latency_ms,
        cost_usd=0.0,
    )

    result = AgentRunResult(
        run_id=run_id or str(uuid.uuid4()),
        genome_id=genome_id,
        answer=answer,
        chunks=chunks,
        candidates=candidates,
        fitness=fitness,
    )
    if persist:
        await persist_run_result(result)
    return result


async def evaluate(
    genome: dict[str, Any],
    query: dict[str, Any],
    run_id: str,
    blackboard: Any,
) -> dict[str, Any]:
    """Compatibility entry point from DAR-9 that returns a persisted evaluation doc."""
    text = str(query["text"])
    ground_truth = query.get("ground_truth")
    result = await run_genome(text, genome, ground_truth=ground_truth, persist=False, run_id=run_id)
    doc = result.to_document()
    doc.update(
        {
            "query_id": str(query.get("_id") or query.get("id") or text),
            "generation": genome.get("generation"),
            "generated_answer": result.answer,
            "coordination_trace": blackboard.snapshot_for(result.genome_id)
            if hasattr(blackboard, "snapshot_for")
            else {},
            "components": result.fitness.as_components(),
            "composite_fitness": result.fitness.composite,
            "timestamp": datetime.now(timezone.utc),
        }
    )
    await _insert_evaluation_doc(doc)
    return doc


async def persist_run_result(result: AgentRunResult) -> None:
    uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI")
    if not uri:
        return
    client = AsyncIOMotorClient(uri)
    db = client[os.environ.get("DB_NAME", "darwin")]
    await db.fitness_evaluations.update_one(
        {"run_id": result.run_id},
        {"$set": result.to_document()},
        upsert=True,
    )


async def _insert_evaluation_doc(doc: dict[str, Any]) -> None:
    uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI")
    if not uri:
        return
    client = AsyncIOMotorClient(uri)
    db = client[os.environ.get("DB_NAME", "darwin")]
    await db.fitness_evaluations.insert_one(doc)
