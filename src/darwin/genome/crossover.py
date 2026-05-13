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
    "search_depth_policy",
    "retrieval_mode_router",
    "hierarchical_traversal_strategy",
    "graph_construction_mode",
    "graph_eagerness",
    "embedding_compression_dim",
    "embedding_quantization",
    "context_utilization_ratio",
)
_COORDINATION_FIELDS = (
    "protocol",
    "consult_threshold",
    "timeout_ms",
    "debate_rounds",
    "signal_decay_rate",
    "pressure_response_sensitivity",
    "sycophancy_spectrum",
    "confidence_calibration",
    "bid_aggressiveness",
    "value_density_estimator",
    "marginal_contribution_threshold",
    "leader_candidacy",
    "capability_embedding",
    "connection_affinity",
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

    Special handling for tag-set lists (`source_routing`, `retrieval_tool_set`):
    union the parents' tags then keep each with 50% probability; fall back to
    p1's full list if the result is empty.

    Vector fields (`capability_embedding`, `connection_affinity`) are picked
    whole from one parent (single-parent inheritance). Component-wise
    interpolation is deferred to Pass 2.
    """

    rng = rng if rng is not None else random.Random()

    retrieval_kwargs = {
        field: _pick(rng, getattr(p1.retrieval_genes, field), getattr(p2.retrieval_genes, field))
        for field in _RETRIEVAL_FIELDS
    }

    source_union = list(dict.fromkeys(
        list(p1.retrieval_genes.source_routing) + list(p2.retrieval_genes.source_routing)
    ))
    source_chosen = [tag for tag in source_union if rng.random() < 0.5]
    if not source_chosen:
        source_chosen = list(p1.retrieval_genes.source_routing)
    retrieval_kwargs["source_routing"] = source_chosen

    tools_union = list(dict.fromkeys(
        list(p1.retrieval_genes.retrieval_tool_set) + list(p2.retrieval_genes.retrieval_tool_set)
    ))
    tools_chosen = [tag for tag in tools_union if rng.random() < 0.5]
    if not tools_chosen:
        tools_chosen = list(p1.retrieval_genes.retrieval_tool_set)
    retrieval_kwargs["retrieval_tool_set"] = tools_chosen

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
