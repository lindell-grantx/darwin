"""End-to-end genome run: retrieve, answer, judge, and persist trace."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from motor.motor_asyncio import AsyncIOMotorClient

from darwin.agents.blackboard import CandidateAnswer
from darwin.agents.coordinator import coordinate
from darwin.fitness.eval_split import EvalSplit, tag_eval_document
from darwin.fitness.judge import JudgeScores, evaluate_answer
from darwin.retrieval.retriever import RetrievedChunk, retrieve

if TYPE_CHECKING:
    from darwin.db.schemas import Attacker


@dataclass(frozen=True)
class AgentRunResult:
    run_id: str
    genome_id: str
    answer: str
    chunks: list[RetrievedChunk]
    candidates: list[CandidateAnswer]
    fitness: JudgeScores
    tool_call_count: int = 0
    process_latency_ms: int | None = None

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


def _apply_attacker(
    *,
    query: str,
    chunks: list[RetrievedChunk],
    attacker: "Attacker | None",
) -> tuple[str, list[RetrievedChunk]]:
    """v2: mutate (query, chunks) per the attacker's attack_vector_type.

    Returns the (attacked_query, attacked_chunks) the coordinator/LLM will see.
    The original `query` is preserved by the caller for fair judging.
    """
    if attacker is None:
        return query, chunks

    vector = attacker.attack_vector_type
    if vector == "corpus_poison":
        # Inject the poison payload as a high-scoring synthetic chunk at the
        # head of the retrieved list. The chunk_id encodes the attacker_id so
        # the trace stays auditable.
        poison = RetrievedChunk(
            chunk_id=f"poison::{attacker.id}",
            text=str(attacker.payload),
            score=1.0,
        )
        return query, [poison, *chunks]
    if vector == "prompt_injection":
        attacked_query = f"{query}\n\n{attacker.payload}"
        return attacked_query, chunks
    if vector == "instruction_override":
        attacked_query = f"{attacker.payload}\n\n{query}"
        return attacked_query, chunks
    return query, chunks


async def run_genome(
    query: str,
    genome: dict[str, Any],
    ground_truth: str | None = None,
    persist: bool = True,
    run_id: str | None = None,
    eval_split: EvalSplit | None = None,
    attacker: "Attacker | None" = None,
) -> AgentRunResult:
    started = time.perf_counter()
    _eval_start = time.monotonic()
    _tool_call_count = 0
    genome_id = str(genome.get("_id") or genome.get("id") or "unknown-genome")
    retrieval_genes = dict(genome.get("retrieval_genes", {}))
    coordination_genes = dict(genome.get("coordination_genes", {}))

    chunks = await retrieve(query, retrieval_genes)
    _tool_call_count += 1
    attacked_query, attacked_chunks = _apply_attacker(
        query=query, chunks=list(chunks), attacker=attacker
    )
    answer, candidates = await coordinate(
        attacked_query, attacked_chunks, coordination_genes, genome=genome
    )
    _tool_call_count += 1
    latency_ms = (time.perf_counter() - started) * 1000
    # Judge always sees the ORIGINAL query so the score reflects the defender's
    # ability to answer the user's true intent under the adversary's pressure.
    fitness = await evaluate_answer(
        query=query,
        answer=answer,
        contexts=[chunk.text for chunk in attacked_chunks],
        ground_truth=ground_truth,
        latency_ms=latency_ms,
        cost_usd=0.0,
    )
    _tool_call_count += 1
    _process_latency_ms = int((time.monotonic() - _eval_start) * 1000)

    result = AgentRunResult(
        run_id=run_id or str(uuid.uuid4()),
        genome_id=genome_id,
        answer=answer,
        chunks=attacked_chunks,
        candidates=candidates,
        fitness=fitness,
        tool_call_count=_tool_call_count,
        process_latency_ms=_process_latency_ms,
    )
    if persist:
        await persist_run_result(result, eval_split=eval_split)
    return result


async def evaluate(
    genome: dict[str, Any],
    query: dict[str, Any],
    run_id: str,
    blackboard: Any,
    eval_split: EvalSplit | None = None,
    attacker: "Attacker | None" = None,
) -> dict[str, Any]:
    """Compatibility entry point from DAR-9 that returns a persisted evaluation doc."""
    text = str(query["text"])
    ground_truth = query.get("ground_truth")
    # Forward `attacker` only when set so legacy mocks of run_genome
    # (which don't accept the new kwarg) keep working.
    extra: dict[str, Any] = {"attacker": attacker} if attacker is not None else {}
    result = await run_genome(
        text,
        genome,
        ground_truth=ground_truth,
        persist=False,
        run_id=run_id,
        **extra,
    )
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
            "attacker_id": attacker.id if attacker is not None else None,
            "tool_call_count": result.tool_call_count,
            "step_coherence": float(result.fitness.groundedness)
            if result.fitness is not None
            else None,
            "process_latency_ms": result.process_latency_ms,
        }
    )
    tag_eval_document(doc, eval_split)
    await _insert_evaluation_doc(doc)
    return doc


async def persist_run_result(
    result: AgentRunResult,
    *,
    eval_split: EvalSplit | None = None,
) -> None:
    uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI")
    if not uri:
        return
    client = AsyncIOMotorClient(uri)
    db = client[os.environ.get("DB_NAME", "darwin")]
    doc = result.to_document()
    tag_eval_document(doc, eval_split)
    await db.fitness_evaluations.update_one(
        {"run_id": result.run_id},
        {"$set": doc},
        upsert=True,
    )


async def _insert_evaluation_doc(doc: dict[str, Any]) -> None:
    uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI")
    if not uri:
        return
    client = AsyncIOMotorClient(uri)
    db = client[os.environ.get("DB_NAME", "darwin")]
    await db.fitness_evaluations.insert_one(doc)
