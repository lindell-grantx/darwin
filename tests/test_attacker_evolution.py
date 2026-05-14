"""Pass 2 PR-2: PAIRED regret fitness."""


def test_paired_regret_zero_when_baseline_equals_best():
    from darwin.attacker.evolution import paired_regret
    r = paired_regret(best_defender_score=0.7, baseline_score=0.7)
    assert r == 0.0


def test_paired_regret_positive_when_best_beats_baseline():
    from darwin.attacker.evolution import paired_regret
    r = paired_regret(best_defender_score=0.8, baseline_score=0.4)
    assert abs(r - 0.4) < 1e-9


def test_paired_regret_zero_when_baseline_beats_best():
    from darwin.attacker.evolution import paired_regret
    r = paired_regret(best_defender_score=0.3, baseline_score=0.6)
    assert r == 0.0
