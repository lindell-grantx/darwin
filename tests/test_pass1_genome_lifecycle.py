"""Pass 1: random_genome + mutate + gene_distance handle all 17 new genes."""

import random

from darwin.genome.factory import random_genome
from darwin.genome.mutate import mutate
from darwin.genome.types import gene_distance


def test_random_genome_samples_all_new_retrieval_genes():
    rng = random.Random(42)
    g = random_genome(rng=rng)
    r = g.retrieval_genes
    assert r.retrieval_mode_router in {"skip", "single_shot", "iterative", "agentic"}
    assert r.hierarchical_traversal_strategy in {
        "single_level", "dual_level", "dfs_pruning", "lca_stopping"
    }
    assert r.graph_construction_mode in {
        "none", "entity_relation", "topic_summary", "rule_graph", "temporal"
    }
    assert 0.0 <= r.graph_eagerness <= 1.0
    assert 40 <= r.embedding_compression_dim <= 2560
    assert r.embedding_quantization in {"float32", "int8", "binary"}
    assert isinstance(r.retrieval_tool_set, list) and r.retrieval_tool_set
    assert 0.0 <= r.context_utilization_ratio <= 1.0


def test_random_genome_samples_all_new_coordination_genes():
    rng = random.Random(42)
    g = random_genome(rng=rng)
    c = g.coordination_genes
    assert 0.0 <= c.pressure_response_sensitivity <= 1.0
    assert -1.0 <= c.sycophancy_spectrum <= 1.0
    assert 0.0 <= c.confidence_calibration <= 1.0
    assert 0.0 <= c.bid_aggressiveness <= 1.0
    assert 0.0 <= c.value_density_estimator <= 1.0
    assert len(c.capability_embedding) == 32
    assert all(-1.0 <= v <= 1.0 for v in c.capability_embedding)
    assert 0.0 <= c.marginal_contribution_threshold <= 1.0
    assert 0.0 <= c.leader_candidacy <= 1.0


def test_mutate_changes_at_least_one_new_gene():
    rng = random.Random(42)
    g = random_genome(rng=rng)
    mutated = mutate(g, rate=1.0, rng=random.Random(99))
    moved = False
    for field in (
        "retrieval_mode_router", "hierarchical_traversal_strategy",
        "graph_construction_mode", "graph_eagerness",
        "embedding_compression_dim", "embedding_quantization",
        "context_utilization_ratio",
    ):
        if getattr(mutated.retrieval_genes, field) != getattr(g.retrieval_genes, field):
            moved = True
            break
    if not moved:
        for field in (
            "pressure_response_sensitivity", "sycophancy_spectrum",
            "confidence_calibration", "bid_aggressiveness",
            "value_density_estimator", "marginal_contribution_threshold",
            "leader_candidacy",
        ):
            if getattr(mutated.coordination_genes, field) != getattr(g.coordination_genes, field):
                moved = True
                break
    assert moved


def test_mutate_handles_capability_embedding_vector():
    rng = random.Random(42)
    g = random_genome(rng=rng)
    mutated = mutate(g, rate=1.0, rng=random.Random(99))
    assert mutated.coordination_genes.capability_embedding != g.coordination_genes.capability_embedding


def test_gene_distance_uses_new_continuous_genes():
    rng = random.Random(42)
    g_a = random_genome(rng=rng)
    g_b = g_a.model_copy(deep=True)
    g_b.retrieval_genes.context_utilization_ratio = (
        0.0 if g_a.retrieval_genes.context_utilization_ratio > 0.5 else 1.0
    )
    g_b.coordination_genes.sycophancy_spectrum = (
        -1.0 if g_a.coordination_genes.sycophancy_spectrum > 0.0 else 1.0
    )
    d_with = gene_distance(g_a, g_b)
    d_without = gene_distance(g_a, g_a.model_copy(deep=True))
    assert d_with > d_without


def test_crossover_propagates_new_genes():
    """uniform_crossover should produce children with valid values for all new genes."""
    from darwin.genome.crossover import uniform_crossover

    rng = random.Random(42)
    p1 = random_genome(rng=rng)
    p2 = random_genome(rng=random.Random(99))
    child = uniform_crossover(p1, p2, generation=1, rng=random.Random(7))

    # Child should have valid (parent-derived) values for each new field
    assert child.retrieval_genes.retrieval_mode_router in (
        p1.retrieval_genes.retrieval_mode_router,
        p2.retrieval_genes.retrieval_mode_router,
    )
    assert child.retrieval_genes.search_depth_policy in (
        p1.retrieval_genes.search_depth_policy,
        p2.retrieval_genes.search_depth_policy,
    )
    assert child.coordination_genes.signal_decay_rate in (
        p1.coordination_genes.signal_decay_rate,
        p2.coordination_genes.signal_decay_rate,
    )
    assert child.coordination_genes.sycophancy_spectrum in (
        p1.coordination_genes.sycophancy_spectrum,
        p2.coordination_genes.sycophancy_spectrum,
    )
    # capability_embedding: child should inherit one parent's vector entirely
    assert (
        child.coordination_genes.capability_embedding == p1.coordination_genes.capability_embedding
        or child.coordination_genes.capability_embedding == p2.coordination_genes.capability_embedding
    )
