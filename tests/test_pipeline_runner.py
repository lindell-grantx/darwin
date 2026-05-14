"""Pass 2 PR-1: pipeline runner translates DAG operators to legacy calls."""

import random

from darwin.agents.pipeline_runner import operator_to_legacy_kwargs
from darwin.genome.pipeline_factory import default_linear_pipeline
from darwin.genome.factory import random_genome


def test_operator_to_legacy_kwargs_chunk():
    g = random_genome(rng=random.Random(0))
    p = default_linear_pipeline(g.retrieval_genes)
    chunk_node = next(n for n in p.nodes if n.stage == "chunk")
    kwargs = operator_to_legacy_kwargs(chunk_node)
    assert kwargs["chunk_size"] == g.retrieval_genes.chunk_size
    assert kwargs["chunk_overlap"] == g.retrieval_genes.chunk_overlap


def test_operator_to_legacy_kwargs_embed():
    g = random_genome(rng=random.Random(0))
    p = default_linear_pipeline(g.retrieval_genes)
    embed_node = next(n for n in p.nodes if n.stage == "embed")
    kwargs = operator_to_legacy_kwargs(embed_node)
    assert "model" in kwargs


def test_operator_to_legacy_kwargs_unknown_stage():
    from darwin.genome.pipeline import PipelineNode
    n = PipelineNode(stage="generate", operator="claude_haiku")
    kwargs = operator_to_legacy_kwargs(n)
    assert isinstance(kwargs, dict)
