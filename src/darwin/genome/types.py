"""Genome helpers — re-exports + diff/distance utilities."""

from __future__ import annotations

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


def gene_diff(a: Genome, b: Genome) -> dict[str, tuple[Any, Any]]:
    """Field-level diff between two genomes' gene layers.

    Returns a dict like {"retrieval_genes.chunk_size": (256, 512), ...}.
    Only includes fields that actually differ. Used for the family-tree UI
    panel and for human-readable "what mutated" displays.
    """

    raise NotImplementedError("B1: implement gene_diff over the three gene layers")


def gene_distance(a: Genome, b: Genome) -> float:
    """Normalized 0..1 distance between two genomes for diversity index.

    Convention: enum/categorical fields contribute 1 if different else 0,
    bounded numeric fields contribute |a-b|/range. Average across all gene
    fields. The population diversity index is mean pairwise distance.
    """

    raise NotImplementedError("B1: implement gene_distance")
