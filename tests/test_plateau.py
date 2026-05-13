"""Pass 1: plateau detector + two-tier model trigger tests."""

from darwin.evolution.plateau import (
    PLATEAU_STDDEV_THRESHOLD,
    is_plateau,
    should_use_opus,
)


def test_is_plateau_true_when_stddev_low():
    fitness_history = [0.71, 0.72, 0.71, 0.73, 0.72, 0.71]
    assert is_plateau(fitness_history) is True


def test_is_plateau_false_when_improving():
    fitness_history = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85]
    assert is_plateau(fitness_history) is False


def test_is_plateau_needs_min_window():
    short = [0.7, 0.71]
    assert is_plateau(short) is False


def test_should_use_opus_every_k_gens():
    assert should_use_opus(generation=10, fitness_history=[0.5]*10) is True
    assert should_use_opus(generation=11, fitness_history=[0.5]*10) is False
    assert should_use_opus(generation=20, fitness_history=[0.5]*10) is True


def test_should_use_opus_on_plateau():
    history = [0.71, 0.72, 0.71, 0.73, 0.72, 0.71]
    assert should_use_opus(generation=7, fitness_history=history) is True
