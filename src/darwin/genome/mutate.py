"""Per-gene mutation operators."""

from __future__ import annotations

import random
from typing import Optional, get_args

from darwin.db.schemas import (
    EMBEDDING_MODELS,
    CoordinationGenes,
    FitnessSummary,
    GenerationGenes,
    Genome,
    ReasoningPattern,
    RetrievalGenes,
)


__all__ = ["mutate"]


_CHUNK_SIZES: tuple[int, ...] = (128, 256, 512, 1024)
_QUERY_TRANSFORMS: tuple[str, ...] = ("none", "hyde", "multi_query", "step_back")
_RERANK: tuple[str, ...] = ("none", "rrf", "voyage-rerank-2")
_PROTOCOLS: tuple[str, ...] = ("solo", "vote", "consult", "debate")
_GENERATOR_MODELS: tuple[str, ...] = (
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
)
_SYSTEM_STYLES: tuple[str, ...] = ("concise", "detailed", "stepwise")
_SOURCE_TAGS: tuple[str, ...] = ("mongodb", "voyage", "langchain")
_REASONING_PATTERNS: tuple[str, ...] = get_args(ReasoningPattern)

_FLOAT_BOUNDS: dict[str, tuple[float, float]] = {
    "chunk_overlap": (0.0, 0.5),
    "confidence_threshold": (0.0, 1.0),
    "consult_threshold": (0.0, 1.0),
    "temperature": (0.0, 1.5),
}

_INT_BOUNDS: dict[str, tuple[int, int]] = {
    "top_k": (1, 50),
    "timeout_ms": (100, 10_000),
    "debate_rounds": (1, 3),
    "max_tokens": (64, 4_096),
}


def _maybe(rng: random.Random, rate: float) -> bool:
    return rng.random() < rate


def _mutate_float(value: float, lo: float, hi: float, rng: random.Random) -> float:
    new = value + rng.gauss(0.0, 0.1)
    if new < lo:
        new = lo
    elif new > hi:
        new = hi
    return new


def _mutate_int(value: int, lo: int, hi: int, rng: random.Random) -> int:
    if rng.random() < 0.25:
        return rng.randint(lo, hi)
    step = rng.choice((-1, 1))
    new = value + step
    if new < lo:
        new = lo
    elif new > hi:
        new = hi
    return new


def _swap_categorical(value, options: tuple, rng: random.Random):
    alternatives = [o for o in options if o != value]
    if not alternatives:
        return value
    return rng.choice(alternatives)


def _mutate_source_routing(current: list[str], rng: random.Random) -> list[str]:
    present = set(current)
    absent = [t for t in _SOURCE_TAGS if t not in present]

    if absent and present:
        if rng.random() < 0.5:
            new_tag = rng.choice(absent)
            return list(present | {new_tag})
        if len(present) > 1:
            drop = rng.choice(list(present))
            kept = [t for t in current if t != drop]
            return kept
        new_tag = rng.choice(absent)
        return list(present | {new_tag})

    if absent:
        new_tag = rng.choice(absent)
        return list(present | {new_tag})

    if len(present) > 1:
        drop = rng.choice(list(present))
        return [t for t in current if t != drop]

    return list(current)


def mutate(
    g: Genome,
    rate: float,
    *,
    rng: Optional[random.Random] = None,
) -> Genome:
    """Return a new Genome with each field independently mutated at probability `rate`.

    Operators (per field type):
    - bounded float: gaussian step `value + rng.gauss(0, 0.1)`, clamped to range
    - categorical/enum/Literal: replace with a uniformly-random different value
    - bounded int: ±1 step (or jump to a random in-range value with 25% prob)
    - list (source_routing): swap one tag in/out, keep non-empty

    The returned genome:
    - has the same id, generation, status, parent_ids as `g` (only gene fields change)
    - resets fitness summary to defaults (mutation invalidates prior eval)
    - rate=0 returns an exact copy (model-validate roundtrip is fine)
    """

    rng = rng if rng is not None else random.Random()

    r = g.retrieval_genes
    c = g.coordination_genes
    gen = g.generation_genes

    embedding_model = (
        _swap_categorical(r.embedding_model, EMBEDDING_MODELS, rng)
        if _maybe(rng, rate) else r.embedding_model
    )
    chunk_size = (
        _swap_categorical(r.chunk_size, _CHUNK_SIZES, rng)
        if _maybe(rng, rate) else r.chunk_size
    )
    chunk_overlap = (
        _mutate_float(r.chunk_overlap, *_FLOAT_BOUNDS["chunk_overlap"], rng)
        if _maybe(rng, rate) else r.chunk_overlap
    )
    query_transform = (
        _swap_categorical(r.query_transform, _QUERY_TRANSFORMS, rng)
        if _maybe(rng, rate) else r.query_transform
    )
    rerank = (
        _swap_categorical(r.rerank, _RERANK, rng)
        if _maybe(rng, rate) else r.rerank
    )
    confidence_threshold = (
        _mutate_float(r.confidence_threshold, *_FLOAT_BOUNDS["confidence_threshold"], rng)
        if _maybe(rng, rate) else r.confidence_threshold
    )
    top_k = (
        _mutate_int(r.top_k, *_INT_BOUNDS["top_k"], rng)
        if _maybe(rng, rate) else r.top_k
    )
    source_routing = (
        _mutate_source_routing(list(r.source_routing), rng)
        if _maybe(rng, rate) else list(r.source_routing)
    )
    if not source_routing:
        source_routing = list(r.source_routing) or ["mongodb"]

    new_retrieval = RetrievalGenes(
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        query_transform=query_transform,
        rerank=rerank,
        confidence_threshold=confidence_threshold,
        top_k=top_k,
        source_routing=source_routing,
    )

    protocol = (
        _swap_categorical(c.protocol, _PROTOCOLS, rng)
        if _maybe(rng, rate) else c.protocol
    )
    consult_threshold = (
        _mutate_float(c.consult_threshold, *_FLOAT_BOUNDS["consult_threshold"], rng)
        if _maybe(rng, rate) else c.consult_threshold
    )
    timeout_ms = (
        _mutate_int(c.timeout_ms, *_INT_BOUNDS["timeout_ms"], rng)
        if _maybe(rng, rate) else c.timeout_ms
    )
    debate_rounds = (
        _mutate_int(c.debate_rounds, *_INT_BOUNDS["debate_rounds"], rng)
        if _maybe(rng, rate) else c.debate_rounds
    )

    new_coord = CoordinationGenes(
        protocol=protocol,
        consult_threshold=consult_threshold,
        timeout_ms=timeout_ms,
        debate_rounds=debate_rounds,
    )

    model = (
        _swap_categorical(gen.model, _GENERATOR_MODELS, rng)
        if _maybe(rng, rate) else gen.model
    )
    temperature = (
        _mutate_float(gen.temperature, *_FLOAT_BOUNDS["temperature"], rng)
        if _maybe(rng, rate) else gen.temperature
    )
    max_tokens = (
        _mutate_int(gen.max_tokens, *_INT_BOUNDS["max_tokens"], rng)
        if _maybe(rng, rate) else gen.max_tokens
    )
    system_style = (
        _swap_categorical(gen.system_style, _SYSTEM_STYLES, rng)
        if _maybe(rng, rate) else gen.system_style
    )
    reasoning_pattern = (
        _swap_categorical(gen.reasoning_pattern, _REASONING_PATTERNS, rng)
        if _maybe(rng, rate) else gen.reasoning_pattern
    )
    self_critique = (
        (not gen.self_critique)
        if _maybe(rng, rate) else gen.self_critique
    )

    new_gen = GenerationGenes(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        system_style=system_style,
        reasoning_pattern=reasoning_pattern,
        self_critique=self_critique,
    )

    return Genome(
        id=g.id,
        generation=g.generation,
        status=g.status,
        parent_ids=list(g.parent_ids),
        retrieval_genes=new_retrieval,
        coordination_genes=new_coord,
        generation_genes=new_gen,
        fitness=FitnessSummary(),
        created_at=g.created_at,
        notes=g.notes,
    )
