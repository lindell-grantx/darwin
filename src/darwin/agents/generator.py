"""Answer generation helpers."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

from darwin.agents.blackboard import CandidateAnswer
from darwin.retrieval.retriever import RetrievedChunk


AGENT_PROMPTS = {
    "retriever": "Answer directly from the retrieved context. Prefer cited facts over speculation.",
    "skeptic": "Look for gaps or contradictions, then produce the most defensible answer.",
    "synthesizer": "Synthesize the strongest points into a concise, complete answer.",
}

FINAL_ANSWER_MARKER = "Final answer:"


def _extract_after(marker: str, text: str) -> str:
    idx = text.rfind(marker)
    return text[idx + len(marker):].strip() if idx != -1 else text.strip()


def _generation_genes(genome: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not genome:
        return {}
    return dict(genome.get("generation_genes") or {})


async def compose(query: str, chunks: list[RetrievedChunk], genome: dict) -> str:
    """Compatibility wrapper from DAR-9 for composing one answer from chunks."""
    candidate = await generate_candidate(query, chunks, "synthesizer", genome=genome)
    return candidate.answer


async def generate_candidate(
    query: str,
    chunks: list[RetrievedChunk],
    agent_name: str = "synthesizer",
    genome: Optional[dict[str, Any]] = None,
) -> CandidateAnswer:
    from darwin.llm.vertex import is_vertex_configured

    if is_vertex_configured():
        try:
            return await _vertex_candidate(query, chunks, agent_name, genome)
        except Exception:
            pass
    return _heuristic_candidate(query, chunks, agent_name)


async def synthesize_final_answer(
    query: str,
    chunks: list[RetrievedChunk],
    candidates: list[CandidateAnswer],
    genome: Optional[dict[str, Any]] = None,
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
        answer = await vertex_complete(
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

    gen_genes = _generation_genes(genome)
    if gen_genes.get("self_critique", False):
        try:
            answer = await _self_critique_pass(query, answer)
        except Exception:
            pass
    return answer


async def _vertex_candidate(
    query: str,
    chunks: list[RetrievedChunk],
    agent_name: str,
    genome: Optional[dict[str, Any]] = None,
) -> CandidateAnswer:
    from darwin.llm.vertex import vertex_complete

    gen_genes = _generation_genes(genome)
    pattern = str(gen_genes.get("reasoning_pattern", "direct"))
    context_block = _context_block(chunks)
    system_prompt = AGENT_PROMPTS.get(agent_name, AGENT_PROMPTS["synthesizer"])

    if pattern == "chain_of_thought":
        user_prompt = (
            f"Question: {query}\n\n"
            f"Context:\n{context_block}\n\n"
            "Think step by step about what the context tells us, then output your "
            f"final answer prefixed with '{FINAL_ANSWER_MARKER}'"
        )
    elif pattern == "reflect_then_answer":
        user_prompt = (
            f"Question: {query}\n\n"
            f"Context:\n{context_block}\n\n"
            "1. Draft an answer.\n"
            "2. Critique your draft for accuracy and groundedness.\n"
            f"3. Output the revised final answer prefixed with '{FINAL_ANSWER_MARKER}'."
        )
    else:
        user_prompt = (
            f"Question: {query}\n\n"
            f"Retrieved context:\n{context_block}\n\n"
            "Return a concise answer grounded in the context."
        )

    raw = await vertex_complete(
        system=system_prompt,
        user=user_prompt,
        max_tokens=2048,
        thinking=True,
    )

    if pattern in ("chain_of_thought", "reflect_then_answer"):
        answer = _extract_after(FINAL_ANSWER_MARKER, raw)
    else:
        answer = raw.strip()

    if gen_genes.get("self_critique", False):
        try:
            answer = await _self_critique_pass(query, answer)
        except Exception:
            pass

    confidence = _confidence_from_chunks(chunks)
    return CandidateAnswer(agent_name=agent_name, answer=answer, confidence=confidence)


async def _self_critique_pass(query: str, answer: str) -> str:
    from darwin.llm.vertex import vertex_complete

    raw = await vertex_complete(
        system="You are a careful reviewer that improves answers for groundedness and accuracy.",
        user=(
            f"Original question: {query}\n\n"
            f"Proposed answer: {answer}\n\n"
            "Critique this answer's groundedness and accuracy. Then output the "
            f"improved version after '{FINAL_ANSWER_MARKER}'."
        ),
        max_tokens=2048,
        thinking=True,
    )
    return _extract_after(FINAL_ANSWER_MARKER, raw)


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
