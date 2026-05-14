"""Pass 2 PR-1: pipeline schema validation."""

import pytest

from darwin.genome.pipeline import (
    STAGE_ORDER,
    PipelineEdge,
    PipelineNode,
    RetrievalPipeline,
)


def test_stage_order_is_nine():
    assert len(STAGE_ORDER) == 9
    assert STAGE_ORDER[0] == "pre_embed_enrich"
    assert STAGE_ORDER[-1] == "post_gen_refine"


def test_node_construction():
    n = PipelineNode(stage="embed", operator="voyage_4", params={"model": "voyage-4"})
    assert n.node_id is not None
    assert n.stage == "embed"
    assert n.operator == "voyage_4"
    assert n.params == {"model": "voyage-4"}


def test_pipeline_with_three_nodes():
    a = PipelineNode(stage="chunk", operator="fixed_size", params={"chunk_size": 512})
    b = PipelineNode(stage="embed", operator="voyage_4", params={})
    c = PipelineNode(stage="retrieve", operator="vector", params={"top_k": 10})
    edges = [
        PipelineEdge(from_id=a.node_id, to_id=b.node_id),
        PipelineEdge(from_id=b.node_id, to_id=c.node_id),
    ]
    p = RetrievalPipeline(nodes=[a, b, c], edges=edges)
    sorted_nodes = p.topological_sort()
    assert [n.node_id for n in sorted_nodes] == [a.node_id, b.node_id, c.node_id]


def test_pipeline_validates_stage_order():
    a = PipelineNode(stage="generate", operator="claude")
    b = PipelineNode(stage="chunk", operator="fixed_size")
    p = RetrievalPipeline(
        nodes=[a, b],
        edges=[PipelineEdge(from_id=a.node_id, to_id=b.node_id)],
    )
    with pytest.raises(ValueError, match="stage order"):
        p.validate_dag()


def test_pipeline_detects_cycle():
    a = PipelineNode(stage="chunk", operator="fixed_size")
    b = PipelineNode(stage="embed", operator="voyage_4")
    p = RetrievalPipeline(
        nodes=[a, b],
        edges=[
            PipelineEdge(from_id=a.node_id, to_id=b.node_id),
            PipelineEdge(from_id=b.node_id, to_id=a.node_id),
        ],
    )
    with pytest.raises(ValueError, match="cycle|order"):
        p.validate_dag()


def test_pipeline_detects_unknown_node_in_edge():
    a = PipelineNode(stage="chunk", operator="fixed_size")
    p = RetrievalPipeline(
        nodes=[a],
        edges=[PipelineEdge(from_id=a.node_id, to_id="nonexistent")],
    )
    with pytest.raises(ValueError, match="unknown"):
        p.validate_dag()


def test_genome_pipeline_field_optional():
    from darwin.db.schemas import Genome
    from darwin.genome.factory import random_genome
    import random
    g = random_genome(rng=random.Random(0))
    assert g.pipeline is None  # default off

    from darwin.genome.pipeline_factory import default_linear_pipeline
    g.pipeline = default_linear_pipeline(g.retrieval_genes)
    assert g.pipeline is not None
    assert len(g.pipeline.nodes) == 5
