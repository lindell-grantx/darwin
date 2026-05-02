"""Uniform crossover between two parent genomes."""

from __future__ import annotations

import random
from typing import Optional

from darwin.db.schemas import (
    CoordinationGenes,
    FitnessSummary,
    GenerationGenes,
    Genome,
    RetrievalGenes,
)


__all__ = ["uniform_crossover"]


_RETRIEVAL_FIELDS = (
    "embedding_model",
    "chunk_size",
    "chunk_overlap",
    "query_transform",
    "rerank",
    "confidence_threshold",
    "top_k",
)
_COORDINATION_FIELDS = (
    "protocol",
    "consult_threshold",
    "timeout_ms",
    "debate_rounds",
)
_GENERATION_FIELDS = (
    "model",
    "temperature",
    "max_tokens",
    "system_style",
)


def _pick(rng: random.Random, a, b):
    return a if rng.random() < 0.5 else b


def uniform_crossover(
    p1: Genome,
    p2: Genome,
    *,
    rng: Optional[random.Random] = None,
    generation: int,
) -> Genome:
    """Per-field uniform crossover.

    For every field across all three gene layers, pick the value from p1 or p2
    with 50/50 probability (independently per field — uniform crossover, not
    single-point). The child:
    - has `parent_ids = [p1.id, p2.id]`
    - has `generation = generation` (the destination generation)
    - has fresh `id`, `status="alive"`, fresh `fitness` summary
    - inherits no fitness data from parents

    Special handling for `source_routing` (a list): pick each tag from p1 with
    50% probability (union semantics); ensure the result is non-empty (fallback
    to p1's full list).
    """

    rng = rng if rng is not None else random.Random()

    retrieval_kwargs = {
        field: _pick(rng, getattr(p1.retrieval_genes, field), getattr(p2.retrieval_genes, field))
        for field in _RETRIEVAL_FIELDS
    }

    union = list(dict.fromkeys(list(p1.retrieval_genes.source_routing) + list(p2.retrieval_genes.source_routing)))
    chosen = [tag for tag in union if rng.random() < 0.5]
    if not chosen:
        chosen = list(p1.retrieval_genes.source_routing)
    retrieval_kwargs["source_routing"] = chosen

    coordination_kwargs = {
        field: _pick(rng, getattr(p1.coordination_genes, field), getattr(p2.coordination_genes, field))
        for field in _COORDINATION_FIELDS
    }
    generation_kwargs = {
        field: _pick(rng, getattr(p1.generation_genes, field), getattr(p2.generation_genes, field))
        for field in _GENERATION_FIELDS
    }

    return Genome(
        generation=generation,
        status="alive",
        parent_ids=[p1.id, p2.id],
        retrieval_genes=RetrievalGenes(**retrieval_kwargs),
        coordination_genes=CoordinationGenes(**coordination_kwargs),
        generation_genes=GenerationGenes(**generation_kwargs),
        fitness=FitnessSummary(),
    )
