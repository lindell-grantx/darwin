# contracts.py — canonical API data contract for Darwin backend↔frontend sync.
# Mirror: ui/lib/contracts.ts — TypeScript counterpart; keep field names and types in sync.
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Gene layers — three-layer genome (ARCHITECTURE.md §1, fleet frozen-decision)
# ---------------------------------------------------------------------------


class RetrievalGenes(BaseModel):
    embedding_model: Literal["gemini_3072", "gemini_1536", "gemini_768", "gemini_256"]
    chunk_size: int  # tokens: 128 | 256 | 512 | 1024
    chunk_overlap: float  # fraction: 0.0 | 0.1 | 0.25 | 0.5
    query_transform: Literal["none", "hyde", "multi_query", "step_back"]
    rerank: Literal["none", "cross_encoder", "llm_rerank", "reciprocal_rank_fusion"]
    confidence_threshold: float = Field(ge=0.0, le=1.0)
    source_routing: list[str]


class CoordinationGenes(BaseModel):
    protocol: Literal["solo", "vote", "consult", "debate"]
    consultation_count: int = Field(ge=0)
    disagreement_resolver: Literal["majority_vote", "highest_confidence", "debate"]
    timeout_ms: int = Field(ge=0)


class DurabilityGenes(BaseModel):
    memory_strategy: Literal["none", "checkpoint", "full_history"]
    checkpoint_every_n_turns: int = Field(ge=1)
    context_compression: Literal["none", "summarize", "truncate"]


# ---------------------------------------------------------------------------
# Fitness
# ---------------------------------------------------------------------------


class FitnessComponents(BaseModel):
    relevance: float = Field(ge=0.0, le=1.0)
    accuracy: float = Field(ge=0.0, le=1.0)
    latency_ms: float = Field(ge=0.0)
    cost_usd: float = Field(ge=0.0)


class FitnessSummary(BaseModel):
    composite: float = Field(ge=0.0, le=1.0)
    last_updated: datetime


# ---------------------------------------------------------------------------
# Genome
# ---------------------------------------------------------------------------


class GenomeSummary(BaseModel):
    id: str
    generation: int
    status: Literal["alive", "retired"]
    fitness: FitnessSummary
    retrieval_genes: RetrievalGenes
    coordination_genes: CoordinationGenes
    durability_genes: DurabilityGenes


class GenomeDetail(GenomeSummary):
    parent_ids: list[str]
    created_at: datetime
    mutation_log: list[str]


# ---------------------------------------------------------------------------
# Retrieval trace
# ---------------------------------------------------------------------------


class RetrievalTraceItem(BaseModel):
    chunk_id: str
    score: float
    position: int


# ---------------------------------------------------------------------------
# Generation summary (fitness-curve / generations endpoints)
# ---------------------------------------------------------------------------


class GenerationRecord(BaseModel):
    generation: int
    population_size: int
    best_fitness: float
    mean_fitness: float
    diversity_index: float
    selection: str
    crossover_rate: float
    mutation_rate: float
    created_at: datetime


class FitnessCurvePoint(BaseModel):
    generation: int
    best: float
    mean: float
    diversity: float


# ---------------------------------------------------------------------------
# Lineage (/lineage/{genome_id})
# ---------------------------------------------------------------------------


class LineageNode(BaseModel):
    id: str
    generation: int
    parent_ids: list[str]
    fitness: FitnessSummary
    retrieval_genes: RetrievalGenes
    is_champion: bool


class LineageResponse(BaseModel):
    genome_id: str
    nodes: list[LineageNode]


# ---------------------------------------------------------------------------
# Champions (/champions)
# ---------------------------------------------------------------------------


class ChampionRecord(BaseModel):
    id: str
    original_genome_id: str
    peak_fitness: float
    generations_alive: int
    lineage: list[str]  # parent_id chain
    retired_at: datetime | None
    genome: GenomeSummary


# ---------------------------------------------------------------------------
# SSE events (/events)
# ---------------------------------------------------------------------------


class EvolutionEvent(BaseModel):
    event_type: Literal[
        "generation.evolved",
        "genome.born",
        "genome.retired",
        "champion.promoted",
        "query.completed",
    ]
    generation: int
    data: dict  # payload varies by event_type
    timestamp: datetime


# ---------------------------------------------------------------------------
# Request / Response shapes for API routes
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    text: str


class QueryResponse(BaseModel):
    run_id: str
    answer: str
    winning_genome: GenomeSummary
    fitness: FitnessComponents
    composite_fitness: float
    retrieval_trace: list[RetrievalTraceItem]


class PopulationResponse(BaseModel):
    genomes: list[GenomeSummary]
    generation: int
    population_size: int
