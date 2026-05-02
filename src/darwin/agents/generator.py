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


async def generate_candidate(
    query: str,
    chunks: list[RetrievedChunk],
    agent_name: str = "synthesizer",
) -> CandidateAnswer:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return await _anthropic_candidate(query, chunks, agent_name)
    return _heuristic_candidate(query, chunks, agent_name)


async def compose(query: str, chunks: list[RetrievedChunk], genome: dict) -> str:
    """Compatibility wrapper from DAR-9 for composing one answer from chunks."""
    candidate = await generate_candidate(query, chunks, "synthesizer")
    return candidate.answer


async def synthesize_final_answer(
    query: str,
    chunks: list[RetrievedChunk],
    candidates: list[CandidateAnswer],
) -> str:
    if not candidates:
        return _contextual_answer(query, chunks)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return max(candidates, key=lambda item: item.confidence).answer

    candidate_block = "\n\n".join(
        f"{candidate.agent_name} (confidence {candidate.confidence:.2f}):\n{candidate.answer}"
        for candidate in candidates
    )
    return await _anthropic_text(
        system="You are Darwin's final answer synthesizer.",
        user=(
            f"Question: {query}\n\n"
            f"Context:\n{_context_block(chunks)}\n\n"
            f"Candidate answers:\n{candidate_block}\n\n"
            "Write the final answer in 1-3 concise paragraphs. Use only supported facts."
        ),
    )


async def _anthropic_candidate(
    query: str,
    chunks: list[RetrievedChunk],
    agent_name: str,
) -> CandidateAnswer:
    text = await _anthropic_text(
        system=AGENT_PROMPTS.get(agent_name, AGENT_PROMPTS["synthesizer"]),
        user=(
            f"Question: {query}\n\n"
            f"Retrieved context:\n{_context_block(chunks)}\n\n"
            "Return a concise answer grounded in the context."
        ),
    )
    confidence = _confidence_from_chunks(chunks)
    return CandidateAnswer(agent_name=agent_name, answer=text, confidence=confidence)


async def _anthropic_text(system: str, user: str) -> str:
    def call() -> str:
        try:
            import anthropic
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install anthropic to use Anthropic generation") from exc

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        message = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
            max_tokens=700,
            temperature=0.2,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in message.content if getattr(block, "type", "") == "text")

    return await asyncio.to_thread(call)


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
