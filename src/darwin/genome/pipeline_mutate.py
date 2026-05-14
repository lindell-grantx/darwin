"""Pass 2: DAG-level mutation operators for RetrievalPipeline.

Three operators:
- swap_operator: pick one node, swap its operator within its stage's catalog
- add_optional_node: insert a node into an unused optional stage
- remove_optional_node: drop a node from an optional stage (never required)

Required stages (chunk/embed/retrieve/generate) always stay present.
Crossover on topology is OUT OF SCOPE for v2.
"""

from __future__ import annotations

import random
from copy import deepcopy

from darwin.genome.pipeline import (
    PipelineEdge,
    PipelineNode,
    RetrievalPipeline,
    STAGE_ORDER,
)
from darwin.genome.pipeline_factory import _OPERATORS_BY_STAGE


REQUIRED_STAGES: tuple[str, ...] = ("chunk", "embed", "retrieve", "generate")
OPTIONAL_STAGES: tuple[str, ...] = tuple(s for s in STAGE_ORDER if s not in REQUIRED_STAGES)


def swap_operator(pipeline: RetrievalPipeline, *, rng: random.Random) -> RetrievalPipeline:
    """Return a copy with one node's operator swapped within its stage catalog."""
    p = deepcopy(pipeline)
    if not p.nodes:
        return p
    node = rng.choice(p.nodes)
    options = _OPERATORS_BY_STAGE.get(node.stage, ())
    alts = [o for o in options if o != node.operator]
    if alts:
        node.operator = rng.choice(alts)
    return p


def add_optional_node(pipeline: RetrievalPipeline, *, rng: random.Random) -> RetrievalPipeline:
    """Insert a node into an optional stage that doesn't already have one."""
    p = deepcopy(pipeline)
    present_stages = {n.stage for n in p.nodes}
    candidates = [s for s in OPTIONAL_STAGES if s not in present_stages]
    if not candidates:
        return p
    new_stage = rng.choice(candidates)
    new_op = rng.choice(_OPERATORS_BY_STAGE[new_stage])
    new_node = PipelineNode(stage=new_stage, operator=new_op, params={})

    p.nodes.append(new_node)
    p.nodes.sort(key=lambda n: STAGE_ORDER.index(n.stage))
    p.edges = [
        PipelineEdge(from_id=p.nodes[i].node_id, to_id=p.nodes[i + 1].node_id)
        for i in range(len(p.nodes) - 1)
    ]
    return p


def remove_optional_node(pipeline: RetrievalPipeline, *, rng: random.Random) -> RetrievalPipeline:
    """Remove a node from an optional stage. No-op if no optional stages present."""
    p = deepcopy(pipeline)
    optional_present = [n for n in p.nodes if n.stage in OPTIONAL_STAGES]
    if not optional_present:
        return p
    drop = rng.choice(optional_present)
    p.nodes = [n for n in p.nodes if n.node_id != drop.node_id]
    p.edges = [
        PipelineEdge(from_id=p.nodes[i].node_id, to_id=p.nodes[i + 1].node_id)
        for i in range(len(p.nodes) - 1)
    ]
    return p


def mutate_pipeline(
    pipeline: RetrievalPipeline,
    rate: float,
    *,
    rng: random.Random,
) -> RetrievalPipeline:
    """Apply DAG-level mutations probabilistically. At rate=1.0 each operator runs once."""
    p = pipeline
    if rng.random() < rate:
        p = swap_operator(p, rng=rng)
    if rng.random() < rate:
        if rng.random() < 0.5:
            p = add_optional_node(p, rng=rng)
        else:
            p = remove_optional_node(p, rng=rng)
    return p
