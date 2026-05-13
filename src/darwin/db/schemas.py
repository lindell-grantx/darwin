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

# v2 MVP collections for adversarial routing (Pass 2).
COLLECTION_ATTACKERS = "attackers"
COLLECTION_NASH_STRATEGIES = "nash_strategies"
COLLECTION_QUERY_TYPE_BUCKETS = "query_type_buckets"


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
SourceTag = Literal["mongodb", "voyage", "langchain", "anthropic", "github"]
CoordinationProtocol = Literal["solo", "vote", "consult", "debate"]
GeneratorModel = Literal[
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
]
GenomeStatus = Literal["alive", "retired", "champion"]
Difficulty = Literal["easy", "medium", "hard"]
EvalSplit = Literal["train", "holdout"]

# Agentic genes — control how the generator actually composes an answer.
# These materially change the runtime path, unlike `system_style` (cosmetic).
ReasoningPattern = Literal[
    "direct",                # one-shot answer from chunks (cheapest, default)
    "chain_of_thought",      # explicit step-by-step before final answer
    "reflect_then_answer",   # draft → self-critique → revised final answer (single LLM call)
]


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
    search_depth_policy: float = Field(default=0.5, ge=0.0, le=1.0,
        description="v2: confidence threshold below which the agent triggers "
                    "additional retrieval rounds. 0.0=always re-retrieve, "
                    "1.0=never re-retrieve. AutoSearch lineage (arXiv 2604.17337).")
    retrieval_mode_router: Literal["skip", "single_shot", "iterative", "agentic"] = Field(
        default="single_shot",
        description="Pass 1: how the agent decides retrieval depth — skip / single-shot / "
                    "iterative refinement / fully agentic loop. AutoSearch + A-RAG lineage.",
    )
    hierarchical_traversal_strategy: Literal[
        "single_level", "dual_level", "dfs_pruning", "lca_stopping"
    ] = Field(
        default="single_level",
        description="Pass 1: hierarchy traversal — single-level / dual-level / DFS-pruning / "
                    "LCA-stopping. BookRAG / T-Retriever lineage.",
    )
    graph_construction_mode: Literal[
        "none", "entity_relation", "topic_summary", "rule_graph", "temporal"
    ] = Field(
        default="none",
        description="Pass 1: graph index mode. none = vector only. entity_relation = MS GraphRAG. "
                    "topic_summary = LightRAG. rule_graph = curated. temporal = T-GRAG.",
    )
    graph_eagerness: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Pass 1: 0.0 = lazy (compute graph at query time, LazyGraphRAG). "
                    "1.0 = eager (full pre-indexing, MS GraphRAG).",
    )
    embedding_compression_dim: int = Field(
        default=1024, ge=40, le=2560,
        description="Pass 1: Matryoshka knob — output embedding dimension. "
                    "Common values: 40, 80, 160, 320, 640, 1280, 2560.",
    )
    embedding_quantization: Literal["float32", "int8", "binary"] = Field(
        default="float32",
        description="Pass 1: quantization for stored embeddings. binary = 32x smaller, "
                    "~2-5% retrieval quality loss.",
    )
    retrieval_tool_set: list[Literal["keyword_search", "semantic_search", "chunk_read"]] = Field(
        default_factory=lambda: ["semantic_search"],
        description="Pass 1: A-RAG-style multi-tool interface. Subset of available retrieval "
                    "tools the agent can choose from per turn.",
    )
    context_utilization_ratio: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Pass 1: fraction of retrieved context to actually pass to LLM. "
                    "0.0 = use no context (zero-shot). 1.0 = pass everything retrieved.",
    )


class CoordinationGenes(_Base):
    protocol: CoordinationProtocol
    consult_threshold: float = Field(ge=0.0, le=1.0, default=0.7)
    timeout_ms: int = Field(ge=100, le=10_000, default=2_000)
    debate_rounds: int = Field(ge=1, le=3, default=2)
    signal_decay_rate: float = Field(default=1.0, ge=0.0, le=1.0,
        description="v2: per-cycle decay rate for blackboard contributions; "
                    "0.0=no decay, 1.0=full decay each cycle. Mandatory per "
                    "stigmergy literature (Pressure-Field, ICLR 2026).")


class GenerationGenes(_Base):
    model: GeneratorModel
    temperature: float = Field(ge=0.0, le=1.5)
    max_tokens: int = Field(ge=64, le=4_096)
    system_style: Literal["concise", "detailed", "stepwise"]
    # Agentic genes — additive defaults so existing docs validate without migration.
    reasoning_pattern: ReasoningPattern = "direct"
    self_critique: bool = False


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
    eval_split: Optional[EvalSplit] = None
    judge_critique: Optional[str] = None
    timestamp: datetime = Field(default_factory=_now)
    attacker_id: Optional[str] = Field(
        default=None,
        description="v2: optional attacker the defender was evaluated against. "
                    "None for clean (no-attacker) evaluations.",
    )


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


# ---------- v2 MVP: adversarial routing ----------


AttackVectorType = Literal["corpus_poison", "prompt_injection", "instruction_override"]


class Attacker(_Base):
    """v2 MVP attacker. Static for week-1 fixtures; evolves in Pass 2."""

    id: str = Field(default_factory=_new_id, alias="_id")
    attack_vector_type: AttackVectorType
    target_query_class: tuple[str, ...] = Field(
        description="Query tag tuple this attacker targets, e.g. ('mongodb', 'vector-search')."
    )
    payload: str = Field(description="The poison chunk or injection text.")
    notes: str = ""
    created_at: datetime = Field(default_factory=_now)


class NashStrategy(_Base):
    """Snapshot of the Nash mixed strategy after a recompute."""

    id: str = Field(default_factory=_new_id, alias="_id")
    weights: dict[str, float] = Field(
        description="defender_id -> weight. Should sum to 1.0."
    )
    snapshot_generation: int
    created_at: datetime = Field(default_factory=_now)


class QueryTypeBucket(_Base):
    """Held-out query-type bucket for the query-axis of two-axis Nash routing."""

    id: str = Field(default_factory=_new_id, alias="_id")
    bucket_key: tuple[str, ...] = Field(description="Tag tuple identifying this bucket.")
    embedding: list[float] = Field(description="Centroid embedding (Voyage-4 1024-dim).")
    n_queries: int = Field(description="Number of seeded queries in this bucket.")
    created_at: datetime = Field(default_factory=_now)
