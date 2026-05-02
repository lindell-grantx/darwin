"""Pydantic schemas for the six Darwin MongoDB collections.

Embedding model: client-side. Chunks carry an `embeddings` sub-document with
one float-vector per Voyage model variant. The seeder calls Voyage and writes
the vectors; the retriever embeds the query text the same way at query time.
Atlas's auto-embed feature is not enabled on this project (org policy).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


COLLECTION_GENOMES = "genomes"
COLLECTION_GENERATIONS = "generations"
COLLECTION_CHUNKS = "chunks"
COLLECTION_QUERIES = "queries"
COLLECTION_FITNESS_EVALUATIONS = "fitness_evaluations"
COLLECTION_CHAMPIONS = "champions"

# Out-of-band collections used for the Hono ↔ Python bridge.
COLLECTION_QUERY_RUNS = "query_runs"
COLLECTION_EVOLUTION_EVENTS = "evolution_events"


EmbeddingModel = Literal[
    "voyage-4-large",
    "voyage-4",
    "voyage-4-lite",
    "voyage-code-3",
]

EMBEDDING_MODELS: tuple[EmbeddingModel, ...] = (
    "voyage-4-large",
    "voyage-4",
    "voyage-4-lite",
    "voyage-code-3",
)

EMBEDDING_DIMS: dict[str, int] = {
    "voyage-4-large": 1024,
    "voyage-4": 1024,
    "voyage-4-lite": 1024,
    "voyage-code-3": 1024,
}


def model_to_field(model: str) -> str:
    """Map a model identifier (with hyphens) to its MongoDB field key."""

    return model.replace("-", "_")
ChunkSize = Literal[128, 256, 512, 1024]
QueryTransform = Literal["none", "hyde", "multi_query", "step_back"]
RerankStrategy = Literal["none", "rrf", "voyage-rerank-2"]
SourceTag = Literal["mongodb", "voyage", "langchain"]
CoordinationProtocol = Literal["solo", "vote", "consult", "debate"]
GeneratorModel = Literal[
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
]
GenomeStatus = Literal["alive", "retired", "champion"]
Difficulty = Literal["easy", "medium", "hard"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid4())


class _Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


# ---------- gene layers ----------


class RetrievalGenes(_Base):
    embedding_model: EmbeddingModel
    chunk_size: ChunkSize
    chunk_overlap: float = Field(ge=0.0, le=0.5)
    query_transform: QueryTransform
    rerank: RerankStrategy
    confidence_threshold: float = Field(ge=0.0, le=1.0)
    top_k: int = Field(ge=1, le=50)
    source_routing: list[SourceTag] = Field(min_length=1)


class CoordinationGenes(_Base):
    protocol: CoordinationProtocol
    consult_threshold: float = Field(ge=0.0, le=1.0, default=0.7)
    timeout_ms: int = Field(ge=100, le=10_000, default=2_000)
    debate_rounds: int = Field(ge=1, le=3, default=2)


class GenerationGenes(_Base):
    model: GeneratorModel
    temperature: float = Field(ge=0.0, le=1.5)
    max_tokens: int = Field(ge=64, le=4_096)
    system_style: Literal["concise", "detailed", "stepwise"]


# ---------- core docs ----------


class FitnessSummary(_Base):
    composite: float = 0.0
    n_evaluations: int = 0
    last_updated: Optional[datetime] = None


class Genome(_Base):
    """One agent variant. Stored one-document-per-genome."""

    id: str = Field(default_factory=_new_id, alias="_id")
    generation: int = Field(ge=0)
    status: GenomeStatus = "alive"
    parent_ids: list[str] = Field(default_factory=list)
    retrieval_genes: RetrievalGenes
    coordination_genes: CoordinationGenes
    generation_genes: GenerationGenes
    fitness: FitnessSummary = Field(default_factory=FitnessSummary)
    created_at: datetime = Field(default_factory=_now)
    notes: Optional[str] = None


class Generation(_Base):
    """Per-generation rollup. Time-series collection (timeField=created_at)."""

    id: str = Field(default_factory=_new_id, alias="_id")
    generation: int = Field(ge=0)
    population_size: int
    best_fitness: float
    mean_fitness: float
    diversity_index: float
    selection: Literal["tournament", "elite", "tournament+elite"]
    crossover_rate: float
    mutation_rate: float
    elite_genome_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)


class Chunk(_Base):
    """Corpus chunk with one embedding vector per Voyage model variant.

    The seeder writes vectors keyed by model field name (hyphens → underscores,
    e.g. `voyage-4-large` → `embeddings.voyage_4_large`). Each vector index is
    bound to one such path.
    """

    id: str = Field(default_factory=_new_id, alias="_id")
    doc_id: str
    text: str
    position: int = Field(ge=0)
    chunk_size: int = Field(ge=1)
    source: SourceTag
    embeddings: dict[str, list[float]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)

    @field_validator("text")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("text must be non-empty")
        return value


class Query(_Base):
    """Eval query. Compatible with the seeded shape from scripts/seed_queries.py."""

    id: str = Field(default_factory=_new_id, alias="_id")
    text: str
    ground_truth: str
    expected_facts: list[str] = Field(min_length=3, max_length=7)
    difficulty: Difficulty
    domain_tags: list[str] = Field(min_length=1)
    seeded: bool = False
    created_at: datetime = Field(default_factory=_now)
    updated_at: Optional[datetime] = None


class FitnessComponents(_Base):
    relevance: float = Field(ge=0.0, le=1.0)
    accuracy: float = Field(ge=0.0, le=1.0)
    coverage: float = Field(ge=0.0, le=1.0)
    latency_ms: int = Field(ge=0)
    cost_usd: float = Field(ge=0.0)


class RetrievalTraceEntry(_Base):
    chunk_id: str
    score: float
    position: int


class FitnessEvaluation(_Base):
    """One (genome, query, run) eval. Insert here triggers the change stream."""

    id: str = Field(default_factory=_new_id, alias="_id")
    genome_id: str
    query_id: str
    generation: int = Field(ge=0)
    run_id: str
    generated_answer: str
    retrieval_trace: list[RetrievalTraceEntry] = Field(default_factory=list)
    coordination_trace: dict[str, Any] = Field(default_factory=dict)
    components: FitnessComponents
    composite_fitness: float = Field(ge=0.0, le=1.0)
    judge_critique: Optional[str] = None
    timestamp: datetime = Field(default_factory=_now)


class Champion(_Base):
    id: str = Field(default_factory=_new_id, alias="_id")
    genome_id: str
    promoted_at_generation: int = Field(ge=0)
    composite_fitness: float
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


# ---------- bridge collections ----------


QueryRunStatus = Literal["pending", "running", "completed", "failed"]


class QueryRun(_Base):
    """Hono → Python work item.

    Hono inserts these with status="pending"; the Python worker tails the
    collection via change stream, claims each by flipping status to "running",
    runs the agent pipeline, and marks completed/failed.
    """

    id: str = Field(default_factory=_new_id, alias="_id")
    text: str
    status: QueryRunStatus = "pending"
    requested_at: datetime = Field(default_factory=_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    target_genome_id: Optional[str] = None
    evaluation_id: Optional[str] = None
    error: Optional[str] = None


EvolutionEventType = Literal[
    "generation.evolved",
    "champion.promoted",
    "population.seeded",
]


class EvolutionEvent(_Base):
    """Out-of-band event sink.

    Time-series collections can't be `watch()`-ed, so the conductor publishes
    a duplicate doc here whenever a generation rolls. Hono's change stream
    on this collection produces the SSE feed for the UI.
    """

    id: str = Field(default_factory=_new_id, alias="_id")
    event_type: EvolutionEventType
    generation: int = Field(ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
