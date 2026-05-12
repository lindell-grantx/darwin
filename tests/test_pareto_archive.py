"""v2 MVP: Pareto-front archive across {easy, medium, hard} difficulty buckets."""

from darwin.evolution.pareto_archive import (
    DIFFICULTY_BUCKETS,
    pareto_front_per_bucket,
    top_k_per_bucket,
)


def test_difficulty_buckets():
    assert DIFFICULTY_BUCKETS == ("easy", "medium", "hard")


def test_pareto_front_protects_specialists():
    """A defender best on 'hard' should be in the archive even if mediocre on 'easy'."""
    fitness = {
        ("d_generalist", "easy"): 0.8,
        ("d_generalist", "medium"): 0.7,
        ("d_generalist", "hard"): 0.6,
        ("d_easy_specialist", "easy"): 0.95,
        ("d_easy_specialist", "medium"): 0.4,
        ("d_easy_specialist", "hard"): 0.3,
        ("d_hard_specialist", "easy"): 0.5,
        ("d_hard_specialist", "medium"): 0.55,
        ("d_hard_specialist", "hard"): 0.85,
    }
    archive = pareto_front_per_bucket(fitness)
    assert "d_hard_specialist" in archive["hard"]
    assert "d_easy_specialist" in archive["easy"]
    assert "d_generalist" in archive["medium"]


def test_pareto_front_handles_ties():
    fitness = {
        ("d_a", "easy"): 0.5,
        ("d_b", "easy"): 0.5,
    }
    archive = pareto_front_per_bucket(fitness)
    assert "d_a" in archive["easy"]
    assert "d_b" in archive["easy"]


def test_top_k_per_bucket_caps():
    fitness = {(f"d_{i}", "easy"): float(i) / 10 for i in range(10)}
    fitness.update({(f"d_{i}", "medium"): 0.0 for i in range(10)})
    fitness.update({(f"d_{i}", "hard"): 0.0 for i in range(10)})

    top3 = top_k_per_bucket(fitness, k=3)
    assert len(top3["easy"]) == 3
    assert top3["easy"] == ["d_9", "d_8", "d_7"]
