"""Pass 1: ShinkaEvolve-style novelty rejection tests."""

import random
import pytest

from darwin.evolution.novelty import (
    cosine_similarity,
    gene_vector,
    novelty_reject,
)


def _stub():
    from darwin.genome.factory import random_genome
    return random_genome(rng=random.Random(0))


def test_gene_vector_returns_floats():
    g = _stub()
    vec = gene_vector(g)
    assert isinstance(vec, list)
    assert all(isinstance(x, float) for x in vec)
    assert len(vec) > 10


def test_gene_vector_deterministic_for_same_genome():
    g = _stub()
    v1 = gene_vector(g)
    v2 = gene_vector(g)
    assert v1 == v2


def test_cosine_similarity_identical_vectors():
    a = [0.5, 0.7, 0.2]
    assert cosine_similarity(a, a) == pytest.approx(1.0)


def test_novelty_reject_identical_genome_rejected():
    g = _stub()
    assert novelty_reject(g, [g], threshold=0.95) is True


def test_novelty_reject_different_genome_accepted():
    g_a = _stub()
    g_b = _stub()
    g_b.retrieval_genes.confidence_threshold = 0.0
    g_b.retrieval_genes.top_k = 1
    g_b.coordination_genes.signal_decay_rate = 0.0
    assert novelty_reject(g_a, [g_b], threshold=0.99) is False


def test_novelty_reject_empty_archive_accepts():
    g = _stub()
    assert novelty_reject(g, [], threshold=0.95) is False
