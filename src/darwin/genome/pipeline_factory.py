"""Pass 2: factories for RetrievalPipeline.

- default_linear_pipeline: convert legacy RetrievalGenes -> equivalent 5-node DAG
- random_pipeline: sample a fresh DAG with one node per required stage and
  zero-or-one node per optional stage (linear chain ordered by stage index)
"""

from __future__ import annotations

import random
from typing import Optional

from darwin.db.schemas import RetrievalGenes
from darwin.genome.pipeline import (
    PipelineEdge,
    PipelineNode,
    RetrievalPipeline,
    STAGE_ORDER,
)


# Operator catalog per stage. Pass 2 ships a small fixed set; future passes
# can grow this by stage as new operators are implemented.
_OPERATORS_BY_STAGE: dict[str, tuple[str, ...]] = {
    "pre_embed_enrich": ("identity", "metadata_inject"),
    "chunk": ("fixed_size", "semantic_paragraph", "sentence_window", "multi_query"),
    "embed": ("voyage_4", "voyage_4_large", "voyage_4_lite", "voyage_4_nano"),
    "retrieve": ("vector", "hybrid", "keyword", "topic_summary"),
    "fuse": ("identity", "rrf"),
    "rerank": ("none", "rrf", "voyage_rerank_2"),
    "post_retrieve_filter": ("identity", "confidence_threshold", "dedupe"),
    "generate": ("claude_haiku", "claude_sonnet"),
    "post_gen_refine": ("identity", "self_critique", "citation_check"),
}


def _embedding_operator_for_model(model: str) -> str:
    """Map RetrievalGenes.embedding_model strings to embed-stage operator keys."""
    candidate = model.replace("-", "_")
    if candidate in _OPERATORS_BY_STAGE["embed"]:
        return candidate
    return "voyage_4"


def default_linear_pipeline(genes: RetrievalGenes) -> RetrievalPipeline:
    """Convert legacy flat RetrievalGenes into an equivalent 5-node linear DAG.

    Stages emitted: chunk -> embed -> retrieve -> rerank -> generate.
    """
    chunk = PipelineNode(
        stage="chunk",
        operator="fixed_size",
        params={"chunk_size": genes.chunk_size, "chunk_overlap": genes.chunk_overlap},
    )
    embed = PipelineNode(
        stage="embed",
        operator=_embedding_operator_for_model(genes.embedding_model),
        params={"model": genes.embedding_model},
    )
    retrieve = PipelineNode(
        stage="retrieve",
        operator="vector",
        params={
            "top_k": genes.top_k,
            "confidence_threshold": genes.confidence_threshold,
            "source_routing": list(genes.source_routing),
        },
    )
    rerank = PipelineNode(
        stage="rerank",
        operator=genes.rerank if genes.rerank in _OPERATORS_BY_STAGE["rerank"] else "none",
        params={},
    )
    generate = PipelineNode(
        stage="generate",
        operator="claude_haiku",
        params={},
    )
    nodes = [chunk, embed, retrieve, rerank, generate]
    edges = [
        PipelineEdge(from_id=nodes[i].node_id, to_id=nodes[i + 1].node_id)
        for i in range(len(nodes) - 1)
    ]
    return RetrievalPipeline(nodes=nodes, edges=edges)


def random_pipeline(*, rng: Optional[random.Random] = None) -> RetrievalPipeline:
    """Sample a fresh DAG with required stages always present + optional stages at p=0.3."""
    rng = rng if rng is not None else random.Random()

    REQUIRED = ("chunk", "embed", "retrieve", "generate")

    nodes: list[PipelineNode] = []
    for stage in STAGE_ORDER:
        if stage in REQUIRED or rng.random() < 0.3:
            operator = rng.choice(_OPERATORS_BY_STAGE[stage])
            nodes.append(PipelineNode(stage=stage, operator=operator, params={}))

    nodes.sort(key=lambda n: STAGE_ORDER.index(n.stage))
    edges = [
        PipelineEdge(from_id=nodes[i].node_id, to_id=nodes[i + 1].node_id)
        for i in range(len(nodes) - 1)
    ]
    return RetrievalPipeline(nodes=nodes, edges=edges)
