"""Random genome factory for genesis generation + offspring fallback."""

from __future__ import annotations

import random
from typing import Optional

from darwin.db.schemas import Genome


__all__ = ["random_genome", "random_population"]


def random_genome(
    generation: int = 0,
    *,
    rng: Optional[random.Random] = None,
    parent_ids: Optional[list[str]] = None,
) -> Genome:
    """Sample a fresh Genome uniformly from the gene space.

    Sample uniformly:
    - retrieval_genes.embedding_model: one of EMBEDDING_MODELS
    - retrieval_genes.chunk_size: one of {128, 256, 512, 1024}
    - retrieval_genes.chunk_overlap: float in [0.0, 0.5]
    - retrieval_genes.query_transform: one of {none, hyde, multi_query, step_back}
    - retrieval_genes.rerank: one of {none, rrf, voyage-rerank-2}
    - retrieval_genes.confidence_threshold: float in [0.0, 1.0]
    - retrieval_genes.top_k: int in [3, 20]
    - retrieval_genes.source_routing: non-empty subset of {mongodb, voyage, langchain}
    - coordination_genes.protocol: one of {solo, vote, consult, debate}
    - coordination_genes.consult_threshold: float in [0.0, 1.0]
    - coordination_genes.timeout_ms: int in [500, 5000]
    - coordination_genes.debate_rounds: int in [1, 3]
    - generation_genes.model: one of {claude-haiku-4-5-20251001, claude-sonnet-4-6}
    - generation_genes.temperature: float in [0.0, 1.0]
    - generation_genes.max_tokens: int in [128, 2048]
    - generation_genes.system_style: one of {concise, detailed, stepwise}

    `parent_ids` defaults to [] (genesis genome). Pass parent ids when this
    factory is used as fallback after a failed crossover.
    """

    raise NotImplementedError("B1: implement random_genome")


def random_population(
    n: int,
    *,
    generation: int = 0,
    rng: Optional[random.Random] = None,
) -> list[Genome]:
    """Sample `n` independent random genomes for genesis."""

    raise NotImplementedError("B1: implement random_population (just a loop)")
