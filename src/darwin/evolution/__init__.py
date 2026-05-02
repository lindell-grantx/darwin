"""Evolution loop: selection, breeding, generation rollover.

Constants are intentionally shared here so all submodules agree on numbers.
"""

POP_SIZE = 24
ELITE_K = 4
N_PARENTS = 16
MUTATION_RATE = 0.15
QUERIES_PER_EVAL = 5
EVALS_PER_GEN_THRESHOLD = POP_SIZE * QUERIES_PER_EVAL  # 120

__all__ = [
    "POP_SIZE",
    "ELITE_K",
    "N_PARENTS",
    "MUTATION_RATE",
    "QUERIES_PER_EVAL",
    "EVALS_PER_GEN_THRESHOLD",
]
