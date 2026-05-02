"""Answer generation helpers."""

from __future__ import annotations

import asyncio
import os

from darwin.agents.blackboard import CandidateAnswer
from darwin.retrieval.retriever import RetrievedChunk


AGENT_PROMPTS = {
    "retriever": "Answer directly from the retrieved context. Prefer cited facts over speculation.",
    "skeptic": "Look for gaps or contradictions, then produce the most defensible answer.",
    "synthesizer": "Synthesize the strongest points into a concise, complete answer.",
}


async def compose(query: str, chunks: list[RetrievedChunk], genome: dict) -> str:
    """Compatibility wrapper from DAR-9 for composing one answer from chunks."""
    candidate = await generate_candidate(query, chunks, "synthesizer")
    return candidate.answer


async def generate_candidate(
    query: str,
    chunks: list[RetrievedChunk],
    agent_name: str = "synthesizer",
) -> CandidateAnswer:
    from darwin.llm.vertex import is_vertex_configured

    if is_vertex_configured():
        try:
            return await _vertex_candidate(query, chunks, agent_name)
        except Exception:
            pass
    return _heuristic_candidate(query, chunks, agent_name)


async def synthesize_final_answer(
    query: str,
    chunks: list[RetrievedChunk],
    candidates: list[CandidateAnswer],
) -> str:
    from darwin.llm.vertex import is_vertex_configured, vertex_complete

    if not candidates:
        return _contextual_answer(query, chunks)
    if not is_vertex_configured():
        return max(candidates, key=lambda item: item.confidence).answer

    candidate_block = "\n\n".join(
        f"{candidate.agent_name} (confidence {candidate.confidence:.2f}):\n{candidate.answer}"
        for candidate in candidates
    )
    try:
        return await vertex_complete(
            system="You are Darwin's final answer synthesizer.",
            user=(
                f"Question: {query}\n\n"
                f"Context:\n{_context_block(chunks)}\n\n"
                f"Candidate answers:\n{candidate_block}\n\n"
                "Write the final answer in 1-3 concise paragraphs. Use only supported facts."
            ),
            max_tokens=2048,
            thinking=True,
        )
    except Exception:
        return max(candidates, key=lambda item: item.confidence).answer


async def _vertex_candidate(
    query: str,
    chunks: list[RetrievedChunk],
    agent_name: str,
) -> CandidateAnswer:
    from darwin.llm.vertex import vertex_complete

    text = await vertex_complete(
        system=AGENT_PROMPTS.get(agent_name, AGENT_PROMPTS["synthesizer"]),
        user=(
            f"Question: {query}\n\n"
            f"Retrieved context:\n{_context_block(chunks)}\n\n"
            "Return a concise answer grounded in the context."
        ),
        max_tokens=2048,
        thinking=True,
    )
    confidence = _confidence_from_chunks(chunks)
    return CandidateAnswer(agent_name=agent_name, answer=text, confidence=confidence)


def _heuristic_candidate(
    query: str,
    chunks: list[RetrievedChunk],
    agent_name: str,
) -> CandidateAnswer:
    return CandidateAnswer(
        agent_name=agent_name,
        answer=_contextual_answer(query, chunks),
        confidence=_confidence_from_chunks(chunks),
        notes="Heuristic generation used because ANTHROPIC_API_KEY is not configured.",
    )


def _contextual_answer(query: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return f"I could not find supporting context for: {query}"
    leading = " ".join(chunk.text.strip() for chunk in chunks[:3] if chunk.text.strip())
    return leading[:900]


def _context_block(chunks: list[RetrievedChunk]) -> str:
    return "\n\n".join(f"[{index}] {chunk.text}" for index, chunk in enumerate(chunks, start=1))


def _confidence_from_chunks(chunks: list[RetrievedChunk]) -> float:
    if not chunks:
        return 0.0
    top_scores = [chunk.score for chunk in chunks[:3]]
    return max(0.0, min(1.0, sum(top_scores) / len(top_scores)))
