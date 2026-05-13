"""Plateau detector + two-tier model triggers.

Signals when the population's best fitness has stalled, prompting Opus
mutation passes (per AlphaEvolve / ShinkaEvolve two-tier pattern).
"""

from __future__ import annotations

import statistics


PLATEAU_WINDOW: int = 5
PLATEAU_STDDEV_THRESHOLD: float = 0.02
OPUS_CADENCE: int = 10


def is_plateau(fitness_history: list[float]) -> bool:
    """True if last PLATEAU_WINDOW fitness values have small but non-zero stddev.

    Pure constancy (stddev == 0) is treated as "no evolution signal yet" rather
    than a true plateau, so it does not trigger the Opus pass.
    """
    if len(fitness_history) < PLATEAU_WINDOW:
        return False
    window = fitness_history[-PLATEAU_WINDOW:]
    stddev = statistics.stdev(window)
    return 0.0 < stddev < PLATEAU_STDDEV_THRESHOLD


def should_use_opus(generation: int, fitness_history: list[float]) -> bool:
    """True if Opus mutation pass should run this generation.

    Triggers:
    - Every OPUS_CADENCE generations
    - On plateau detection
    """
    if generation > 0 and generation % OPUS_CADENCE == 0:
        return True
    if is_plateau(fitness_history):
        return True
    return False
