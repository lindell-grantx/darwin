"""LLM-as-judge fitness scoring."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any


DEFAULT_WEIGHTS = {
    "relevance": 0.35,
    "accuracy": 0.40,
    "coverage": 0.20,
    "latency": 0.03,
    "cost": 0.02,
}


@dataclass(frozen=True)
class JudgeScores:
    relevance: float
    accuracy: float
    coverage: float
    groundedness: float
    latency_ms: float
    cost_usd: float
    composite: float
    rationale: str

    def as_components(self) -> dict[str, float]:
        return {
            "relevance": self.relevance,
            "accuracy": self.accuracy,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
        }


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def composite_score(
    relevance: float,
    accuracy: float,
    coverage: float,
    latency_ms: float,
    cost_usd: float,
    weights: dict[str, float] | None = None,
) -> float:
    scoring_weights = weights or DEFAULT_WEIGHTS
    latency_score = 1.0 - _clamp(latency_ms / 5000.0)
    cost_score = 1.0 - _clamp(cost_usd / 0.05)
    score = (
        scoring_weights["relevance"] * relevance
        + scoring_weights["accuracy"] * accuracy
        + scoring_weights["coverage"] * coverage
        + scoring_weights["latency"] * latency_score
        + scoring_weights["cost"] * cost_score
    )
    return round(_clamp(score), 4)


async def evaluate_answer(
    query: str,
    answer: str,
    contexts: list[str],
    ground_truth: str | None = None,
    latency_ms: float = 0.0,
    cost_usd: float = 0.0,
) -> JudgeScores:
    """Score an answer using Anthropic when available, otherwise lexical fallback."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        result = await _anthropic_judge(query, answer, contexts, ground_truth)
    else:
        result = _heuristic_judge(query, answer, contexts, ground_truth)

    composite = composite_score(
        result["relevance"],
        result["accuracy"],
        result["coverage"],
        latency_ms,
        cost_usd,
    )
    return JudgeScores(
        relevance=result["relevance"],
        accuracy=result["accuracy"],
        coverage=result["coverage"],
        groundedness=result["groundedness"],
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        composite=composite,
        rationale=result["rationale"],
    )


async def _anthropic_judge(
    query: str,
    answer: str,
    contexts: list[str],
    ground_truth: str | None,
) -> dict[str, Any]:
    prompt = {
        "query": query,
        "answer": answer,
        "retrieved_contexts": contexts,
        "ground_truth": ground_truth,
        "instructions": (
            "Return JSON with relevance, accuracy, coverage, groundedness values "
            "from 0 to 1 and a short rationale."
        ),
    }

    def call() -> dict[str, Any]:
        try:
            import anthropic
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install anthropic to use the Anthropic judge") from exc

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        message = client.messages.create(
            model=os.environ.get("ANTHROPIC_JUDGE_MODEL", "claude-3-5-sonnet-latest"),
            max_tokens=500,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Judge this RAG answer. Respond with JSON only.\n"
                        f"{json.dumps(prompt, ensure_ascii=False)}"
                    ),
                }
            ],
        )
        text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text")
        return _normalize_judge_payload(json.loads(text))

    return await asyncio.to_thread(call)


def _heuristic_judge(
    query: str,
    answer: str,
    contexts: list[str],
    ground_truth: str | None,
) -> dict[str, Any]:
    answer_terms = _terms(answer)
    query_terms = _terms(query)
    context_terms = _terms(" ".join(contexts))
    truth_terms = _terms(ground_truth or "")

    relevance = _overlap(answer_terms, query_terms)
    groundedness = _overlap(answer_terms, context_terms)
    accuracy = _overlap(answer_terms, truth_terms) if truth_terms else groundedness
    coverage = min(1.0, len(answer_terms) / 80.0)

    return _normalize_judge_payload(
        {
            "relevance": max(relevance, 0.2 if answer.strip() else 0.0),
            "accuracy": accuracy,
            "coverage": coverage,
            "groundedness": groundedness,
            "rationale": "Heuristic judge used because ANTHROPIC_API_KEY is not configured.",
        }
    )


def _normalize_judge_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "relevance": _clamp(float(payload.get("relevance", 0.0))),
        "accuracy": _clamp(float(payload.get("accuracy", 0.0))),
        "coverage": _clamp(float(payload.get("coverage", 0.0))),
        "groundedness": _clamp(float(payload.get("groundedness", 0.0))),
        "rationale": str(payload.get("rationale", "")),
    }


def _terms(text: str) -> set[str]:
    return {part.strip(".,:;!?()[]{}").lower() for part in text.split() if len(part.strip()) > 2}


def _overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, len(right))
