"""Random genome factory for genesis generation + offspring fallback."""

from __future__ import annotations

import random
from typing import Optional, get_args

from darwin.db.schemas import (
    EMBEDDING_MODELS,
    CoordinationGenes,
    CoordinationProtocol,
    GenerationGenes,
    GeneratorModel,
    Genome,
    QueryTransform,
    RerankStrategy,
    RetrievalGenes,
    SourceTag,
)


__all__ = ["random_genome", "random_population"]


_QUERY_TRANSFORMS: tuple[str, ...] = get_args(QueryTransform)
_RERANK_STRATEGIES: tuple[str, ...] = get_args(RerankStrategy)
_SOURCE_TAGS: tuple[str, ...] = get_args(SourceTag)
_PROTOCOLS: tuple[str, ...] = get_args(CoordinationProtocol)
_GENERATOR_MODELS: tuple[str, ...] = get_args(GeneratorModel)
_SYSTEM_STYLES: tuple[str, ...] = ("concise", "detailed", "stepwise")
_CHUNK_SIZES: tuple[int, ...] = (128, 256, 512, 1024)


def _sample_source_routing(rng: random.Random) -> list[str]:
    # Non-empty subset of _SOURCE_TAGS, uniform over the 2^n - 1 non-empty
    # subsets. We do that by including each tag iid p=0.5 and re-rolling
    # if we end up with the empty set.
    while True:
        subset = [tag for tag in _SOURCE_TAGS if rng.random() < 0.5]
        if subset:
            return subset


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

    if rng is None:
        rng = random.Random()
    if parent_ids is None:
        parent_ids = []

    retrieval = RetrievalGenes(
        embedding_model=rng.choice(EMBEDDING_MODELS),
        chunk_size=rng.choice(_CHUNK_SIZES),
        chunk_overlap=rng.uniform(0.0, 0.5),
        query_transform=rng.choice(_QUERY_TRANSFORMS),
        rerank=rng.choice(_RERANK_STRATEGIES),
        confidence_threshold=rng.uniform(0.0, 1.0),
        top_k=rng.randint(3, 20),
        source_routing=_sample_source_routing(rng),
    )

    coordination = CoordinationGenes(
        protocol=rng.choice(_PROTOCOLS),
        consult_threshold=rng.uniform(0.0, 1.0),
        timeout_ms=rng.randint(500, 5000),
        debate_rounds=rng.randint(1, 3),
    )

    generation_genes = GenerationGenes(
        model=rng.choice(_GENERATOR_MODELS),
        temperature=rng.uniform(0.0, 1.0),
        max_tokens=rng.randint(128, 2048),
        system_style=rng.choice(_SYSTEM_STYLES),
    )

    return Genome(
        generation=generation,
        parent_ids=list(parent_ids),
        retrieval_genes=retrieval,
        coordination_genes=coordination,
        generation_genes=generation_genes,
    )


def random_population(
    n: int,
    *,
    generation: int = 0,
    rng: Optional[random.Random] = None,
) -> list[Genome]:
    """Sample `n` independent random genomes for genesis."""

    if rng is None:
        rng = random.Random()
    return [random_genome(generation=generation, rng=rng) for _ in range(n)]
