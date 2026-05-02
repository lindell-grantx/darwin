"""Genome-driven agent coordination protocols."""

from __future__ import annotations

import asyncio
from typing import Any

from darwin.agents.blackboard import Blackboard, CandidateAnswer
from darwin.agents.generator import generate_candidate, synthesize_final_answer


def _gene(genes: dict[str, Any], name: str, default: Any) -> Any:
    return genes.get(name, default)


async def coordinate(query: str, chunks: list[Any], genes: dict[str, Any]) -> tuple[str, list[CandidateAnswer]]:
    protocol = str(_gene(genes, "protocol", "solo"))
    blackboard = Blackboard(query=query, chunks=chunks)

    if protocol == "solo":
        candidate = await generate_candidate(query, chunks, "synthesizer")
        blackboard.add_candidate(candidate)
        return candidate.answer, blackboard.candidates

    agent_names = _agent_roster(protocol, int(_gene(genes, "consultation_count", 2)))
    candidates = await asyncio.gather(
        *(generate_candidate(query, chunks, agent_name) for agent_name in agent_names)
    )
    for candidate in candidates:
        blackboard.add_candidate(candidate)

    resolver = str(_gene(genes, "disagreement_resolver", "highest_confidence"))
    if protocol == "debate" or resolver == "debate":
        final = await synthesize_final_answer(query, chunks, blackboard.candidates)
        return final, blackboard.candidates

    if resolver == "majority_vote":
        return _majority_vote(blackboard.candidates).answer, blackboard.candidates

    return blackboard.highest_confidence().answer, blackboard.candidates


async def execute_protocol(
    genome: dict[str, Any],
    query: str,
    blackboard: Blackboard,
) -> tuple[str, list[Any]]:
    """Compatibility entry point from DAR-9: retrieve, coordinate, and publish trace."""
    from darwin.retrieval.retriever import retrieve

    genome_id = str(genome.get("_id") or genome.get("id") or "unknown-genome")
    retrieval_genes = dict(genome.get("retrieval_genes", {}))
    coordination_genes = dict(genome.get("coordination_genes", {}))
    blackboard.protocol = str(_gene(coordination_genes, "protocol", "solo"))

    chunks = await retrieve(query, retrieval_genes)
    answer, candidates = await coordinate(query, chunks, coordination_genes)

    if candidates:
        winner = max(candidates, key=lambda item: item.confidence)
        await blackboard.publish_proposal(genome_id, answer, winner.confidence, chunks)
    return answer, chunks


def _agent_roster(protocol: str, consultation_count: int) -> list[str]:
    if protocol == "consult":
        return ["synthesizer"] + ["retriever"] * max(1, consultation_count)
    if protocol == "vote":
        return ["retriever", "skeptic", "synthesizer"][: max(1, consultation_count + 1)]
    if protocol == "debate":
        return ["retriever", "skeptic", "synthesizer"]
    return ["synthesizer"]


def _majority_vote(candidates: list[CandidateAnswer]) -> CandidateAnswer:
    if not candidates:
        raise ValueError("No candidate answers available")
    normalized: dict[str, tuple[int, CandidateAnswer]] = {}
    for candidate in candidates:
        key = candidate.answer.strip().lower()
        count, existing = normalized.get(key, (0, candidate))
        normalized[key] = (count + 1, existing)
    _, winner = max(normalized.values(), key=lambda item: (item[0], item[1].confidence))
    return winner
