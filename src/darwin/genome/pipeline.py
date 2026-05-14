"""Pass 2: typed 9-stage DAG retrieval pipeline (RAGSmith taxonomy).

Replaces flat RetrievalGenes when set on Genome.pipeline. Each node belongs to
one of nine canonical stages and carries an operator + parameters. Edges define
data flow.

Crossover for DAGs is unsolved at v2; topology mutates only via add/remove edge
and add/remove node operations. Per-node parameters mutate via the same
mechanical/reflective operators used in Pass 1. Crossover continues to operate
on coordination + durability flat blocks.

Reference: RAGSmith (arXiv:2511.01386), AFlow (arXiv:2410.10762).
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


StageType = Literal[
    "pre_embed_enrich",
    "chunk",
    "embed",
    "retrieve",
    "fuse",
    "rerank",
    "post_retrieve_filter",
    "generate",
    "post_gen_refine",
]


STAGE_ORDER: tuple[str, ...] = (
    "pre_embed_enrich",
    "chunk",
    "embed",
    "retrieve",
    "fuse",
    "rerank",
    "post_retrieve_filter",
    "generate",
    "post_gen_refine",
)


def _stage_index(stage: str) -> int:
    return STAGE_ORDER.index(stage)


def _new_id() -> str:
    return str(uuid.uuid4())


class PipelineNode(BaseModel):
    """One node in the DAG retrieval pipeline."""

    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(default_factory=_new_id)
    stage: StageType
    operator: str = Field(description="Operator implementation key, e.g. voyage_4_embed.")
    params: dict[str, Any] = Field(default_factory=dict)


class PipelineEdge(BaseModel):
    """Directed edge from upstream node to downstream node."""

    model_config = ConfigDict(extra="forbid")

    from_id: str
    to_id: str


class RetrievalPipeline(BaseModel):
    """DAG of pipeline nodes. Replaces flat RetrievalGenes when set."""

    model_config = ConfigDict(extra="forbid")

    nodes: list[PipelineNode]
    edges: list[PipelineEdge] = Field(default_factory=list)

    def validate_dag(self) -> None:
        """Raise ValueError if cycle, unknown edge endpoints, or stage-order violation."""
        node_ids = {n.node_id for n in self.nodes}
        node_by_id = {n.node_id: n for n in self.nodes}

        for e in self.edges:
            if e.from_id not in node_ids:
                raise ValueError(f"edge references unknown node {e.from_id}")
            if e.to_id not in node_ids:
                raise ValueError(f"edge references unknown node {e.to_id}")
            if _stage_index(node_by_id[e.from_id].stage) > _stage_index(node_by_id[e.to_id].stage):
                raise ValueError(
                    f"edge violates stage order: {node_by_id[e.from_id].stage} -> "
                    f"{node_by_id[e.to_id].stage}"
                )

        # Cycle check via Kahn's algorithm
        in_degree = {nid: 0 for nid in node_ids}
        for e in self.edges:
            in_degree[e.to_id] += 1
        queue = [nid for nid, d in in_degree.items() if d == 0]
        seen = 0
        while queue:
            nid = queue.pop(0)
            seen += 1
            for e in self.edges:
                if e.from_id == nid:
                    in_degree[e.to_id] -= 1
                    if in_degree[e.to_id] == 0:
                        queue.append(e.to_id)
        if seen != len(node_ids):
            raise ValueError("pipeline has cycle")

    def topological_sort(self) -> list[PipelineNode]:
        """Return nodes in topological order (stable: ties broken by stage index)."""
        self.validate_dag()
        node_by_id = {n.node_id: n for n in self.nodes}
        in_degree = {nid: 0 for nid in node_by_id}
        for e in self.edges:
            in_degree[e.to_id] += 1
        ready = sorted(
            [nid for nid, d in in_degree.items() if d == 0],
            key=lambda nid: _stage_index(node_by_id[nid].stage),
        )
        out: list[PipelineNode] = []
        while ready:
            nid = ready.pop(0)
            out.append(node_by_id[nid])
            new_ready = []
            for e in self.edges:
                if e.from_id == nid:
                    in_degree[e.to_id] -= 1
                    if in_degree[e.to_id] == 0:
                        new_ready.append(e.to_id)
            ready.extend(sorted(new_ready, key=lambda x: _stage_index(node_by_id[x].stage)))
        return out
