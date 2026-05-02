"""Shared evidence and candidate answer state for agent coordination."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from darwin.retrieval.retriever import RetrievedChunk


@dataclass(frozen=True)
class CandidateAnswer:
    agent_name: str
    answer: str
    confidence: float
    notes: str = ""


class Blackboard:
    def __init__(
        self,
        run_id: str = "",
        query: str = "",
        genomes: list[dict[str, Any]] | None = None,
        chunks: list[RetrievedChunk] | None = None,
    ) -> None:
        self.run_id = run_id
        self.query = query
        self.genomes = genomes or []
        self.chunks = chunks or []
        self.candidates: list[CandidateAnswer] = []
        self.proposals: dict[str, dict[str, Any]] = {}
        self.votes: dict[str, dict[str, Any]] = {}
        self.protocol = ""

    def context_text(self) -> str:
        return "\n\n".join(
            f"[{index}] {chunk.text}" for index, chunk in enumerate(self.chunks, start=1)
        )

    def add_candidate(self, candidate: CandidateAnswer) -> None:
        self.candidates.append(candidate)

    def highest_confidence(self) -> CandidateAnswer:
        if not self.candidates:
            raise ValueError("No candidate answers available")
        return max(self.candidates, key=lambda item: item.confidence)

    async def publish_proposal(
        self,
        genome_id: str,
        draft: str,
        confidence: float,
        chunks: list[RetrievedChunk],
    ) -> None:
        self.proposals[genome_id] = {
            "draft": draft,
            "confidence": confidence,
            "chunks": [
                {"chunk_id": chunk.chunk_id, "score": chunk.score, "text": chunk.text}
                for chunk in chunks
            ],
        }

    async def gather(self, timeout_ms: int) -> list[dict[str, Any]]:
        return list(self.proposals.values())

    async def cast_vote(self, genome_id: str, voted_for: str, reason: str) -> None:
        self.votes[genome_id] = {"voted_for": voted_for, "reason": reason}

    def snapshot_for(self, genome_id: str) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "query": self.query,
            "protocol": self.protocol,
            "proposal": self.proposals.get(genome_id),
            "vote": self.votes.get(genome_id),
            "visible_proposals": self.proposals,
        }
