"""Pass 2 PR-1: pipeline factory tests."""

import random

from darwin.genome.factory import random_genome
from darwin.genome.pipeline import RetrievalPipeline
from darwin.genome.pipeline_factory import (
    default_linear_pipeline,
    random_pipeline,
)


def test_default_linear_pipeline_from_flat_genes():
    g = random_genome(rng=random.Random(0))
    p = default_linear_pipeline(g.retrieval_genes)
    assert isinstance(p, RetrievalPipeline)
    stages = [n.stage for n in p.topological_sort()]
    assert stages == ["chunk", "embed", "retrieve", "rerank", "generate"]
    assert len(p.edges) == 4


def test_default_linear_pipeline_propagates_genes_into_params():
    g = random_genome(rng=random.Random(0))
    p = default_linear_pipeline(g.retrieval_genes)
    sorted_nodes = p.topological_sort()
    chunk_node = sorted_nodes[0]
    assert chunk_node.params["chunk_size"] == g.retrieval_genes.chunk_size


def test_random_pipeline_yields_valid_dag():
    rng = random.Random(42)
    p = random_pipeline(rng=rng)
    p.validate_dag()
    stages = {n.stage for n in p.nodes}
    assert {"chunk", "embed", "retrieve", "generate"}.issubset(stages)


def test_random_pipeline_deterministic_with_seed():
    p1 = random_pipeline(rng=random.Random(42))
    p2 = random_pipeline(rng=random.Random(42))
    assert [n.stage for n in p1.topological_sort()] == [n.stage for n in p2.topological_sort()]
