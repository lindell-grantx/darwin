"""Genome helpers — re-exports + diff/distance utilities."""

from __future__ import annotations

import math
from typing import Any

from darwin.db.schemas import (
    EMBEDDING_MODELS,
    CoordinationGenes,
    EmbeddingModel,
    Genome,
    GenerationGenes,
    RetrievalGenes,
)


__all__ = [
    "CoordinationGenes",
    "EMBEDDING_MODELS",
    "EmbeddingModel",
    "Genome",
    "GenerationGenes",
    "RetrievalGenes",
    "gene_diff",
    "gene_distance",
]


# Layers walked by both gene_diff and gene_distance. Keeping this tuple in one
# place keeps the two utilities in lock-step.
_GENE_LAYERS: tuple[str, ...] = (
    "retrieval_genes",
    "coordination_genes",
    "generation_genes",
)


# Numeric field ranges used for distance normalization. Values mirror the
# sampling spec in factory.random_genome so that "distance 1.0" means
# "endpoints of the realised gene space".
_NUMERIC_RANGES: dict[str, tuple[float, float]] = {
    "retrieval_genes.chunk_overlap": (0.0, 0.5),
    "retrieval_genes.confidence_threshold": (0.0, 1.0),
    "retrieval_genes.top_k": (3.0, 20.0),
    "retrieval_genes.search_depth_policy": (0.0, 1.0),
    "coordination_genes.consult_threshold": (0.0, 1.0),
    "coordination_genes.timeout_ms": (500.0, 5000.0),
    "coordination_genes.debate_rounds": (1.0, 3.0),
    "coordination_genes.signal_decay_rate": (0.0, 1.0),
    "generation_genes.temperature": (0.0, 1.0),
    "generation_genes.max_tokens": (128.0, 2048.0),
}

_NUMERIC_RANGES.update({
    "retrieval_genes.graph_eagerness": (0.0, 1.0),
    "retrieval_genes.context_utilization_ratio": (0.0, 1.0),
    "retrieval_genes.embedding_compression_dim": (40.0, 2560.0),
    "coordination_genes.pressure_response_sensitivity": (0.0, 1.0),
    "coordination_genes.sycophancy_spectrum": (-1.0, 1.0),
    "coordination_genes.confidence_calibration": (0.0, 1.0),
    "coordination_genes.bid_aggressiveness": (0.0, 1.0),
    "coordination_genes.value_density_estimator": (0.0, 1.0),
    "coordination_genes.marginal_contribution_threshold": (0.0, 1.0),
    "coordination_genes.leader_candidacy": (0.0, 1.0),
})


# chunk_size is an ordered categorical: {128, 256, 512, 1024}. Treat it as
# numeric on the index axis so neighbouring sizes are "closer" than extremes.
_CHUNK_SIZES: tuple[int, ...] = (128, 256, 512, 1024)


def _iter_gene_fields(genome: Genome):
    for layer in _GENE_LAYERS:
        layer_obj = getattr(genome, layer)
        for field_name in layer_obj.__class__.model_fields:
            yield layer, field_name, getattr(layer_obj, field_name)


def gene_diff(a: Genome, b: Genome) -> dict[str, tuple[Any, Any]]:
    """Field-level diff between two genomes' gene layers.

    Returns a dict like {"retrieval_genes.chunk_size": (256, 512), ...}.
    Only includes fields that actually differ. Used for the family-tree UI
    panel and for human-readable "what mutated" displays.
    """

    diff: dict[str, tuple[Any, Any]] = {}
    for layer in _GENE_LAYERS:
        layer_a = getattr(a, layer)
        layer_b = getattr(b, layer)
        for field_name in layer_a.__class__.model_fields:
            val_a = getattr(layer_a, field_name)
            val_b = getattr(layer_b, field_name)
            if isinstance(val_a, list) and isinstance(val_b, list):
                # Order-insensitive compare for source_routing-style lists.
                if sorted(val_a) != sorted(val_b):
                    diff[f"{layer}.{field_name}"] = (val_a, val_b)
            else:
                if val_a != val_b:
                    diff[f"{layer}.{field_name}"] = (val_a, val_b)
    return diff


def _field_distance(path: str, val_a: Any, val_b: Any) -> float:
    if path == "retrieval_genes.chunk_size":
        idx_a = _CHUNK_SIZES.index(val_a)
        idx_b = _CHUNK_SIZES.index(val_b)
        return abs(idx_a - idx_b) / (len(_CHUNK_SIZES) - 1)

    if path in ("retrieval_genes.source_routing", "retrieval_genes.retrieval_tool_set"):
        set_a = set(val_a)
        set_b = set(val_b)
        union = set_a | set_b
        if not union:
            return 0.0
        return 1.0 - (len(set_a & set_b) / len(union))

    if path == "coordination_genes.capability_embedding":
        if not val_a or not val_b or len(val_a) != len(val_b):
            return 1.0
        dot = sum(x * y for x, y in zip(val_a, val_b))
        norm_a = math.sqrt(sum(x * x for x in val_a))
        norm_b = math.sqrt(sum(y * y for y in val_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        cos = dot / (norm_a * norm_b)
        return (1.0 - cos) / 2.0  # [-1,1] cosine -> [0,1] distance

    if path == "coordination_genes.connection_affinity":
        if not val_a and not val_b:
            return 0.0
        return abs(len(val_a) - len(val_b)) / max(1, max(len(val_a), len(val_b)))

    if path in _NUMERIC_RANGES:
        lo, hi = _NUMERIC_RANGES[path]
        span = hi - lo
        if span <= 0:
            return 0.0
        delta = abs(float(val_a) - float(val_b)) / span
        return min(1.0, max(0.0, delta))

    # Categorical / enum / anything else: 1 if different, 0 if equal.
    return 0.0 if val_a == val_b else 1.0


def gene_distance(a: Genome, b: Genome) -> float:
    """Normalized 0..1 distance between two genomes for diversity index.

    Convention: enum/categorical fields contribute 1 if different else 0,
    bounded numeric fields contribute |a-b|/range. Average across all gene
    fields. The population diversity index is mean pairwise distance.
    """

    total = 0.0
    count = 0
    for layer in _GENE_LAYERS:
        layer_a = getattr(a, layer)
        layer_b = getattr(b, layer)
        for field_name in layer_a.__class__.model_fields:
            path = f"{layer}.{field_name}"
            val_a = getattr(layer_a, field_name)
            val_b = getattr(layer_b, field_name)
            total += _field_distance(path, val_a, val_b)
            count += 1
    if count == 0:
        return 0.0
    result = total / count
    # Clamp for paranoia — every per-field contribution is already in [0, 1].
    return min(1.0, max(0.0, result))
