"""v2 MVP: random_genome + mutate + gene_distance handle new genes."""

import random

from darwin.genome.factory import random_genome
from darwin.genome.mutate import mutate
from darwin.genome.types import gene_distance


def test_random_genome_includes_new_genes():
    rng = random.Random(42)
    g = random_genome(rng=rng)
    assert 0.0 <= g.coordination_genes.signal_decay_rate <= 1.0
    assert 0.0 <= g.retrieval_genes.search_depth_policy <= 1.0


def test_mutate_can_change_new_genes():
    rng = random.Random(42)
    g = random_genome(rng=rng)
    mutated = mutate(g, rate=1.0, rng=random.Random(99))
    moved = (
        mutated.coordination_genes.signal_decay_rate
        != g.coordination_genes.signal_decay_rate
        or mutated.retrieval_genes.search_depth_policy
        != g.retrieval_genes.search_depth_policy
    )
    assert moved


def test_gene_distance_uses_new_genes():
    rng = random.Random(42)
    g_a = random_genome(rng=rng)
    g_b = g_a.model_copy(deep=True)
    g_b.coordination_genes.signal_decay_rate = 0.0 if g_a.coordination_genes.signal_decay_rate > 0.5 else 1.0
    g_b.retrieval_genes.search_depth_policy = 0.0 if g_a.retrieval_genes.search_depth_policy > 0.5 else 1.0
    d_with = gene_distance(g_a, g_b)
    g_c = g_a.model_copy(deep=True)
    d_without = gene_distance(g_a, g_c)
    assert d_with > d_without
