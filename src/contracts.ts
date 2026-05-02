// Canonical API ↔ UI contracts.
// Imported by both the Hono server (server/src/) and the Vite UI (frontend/src/ via @contracts alias).
// Mirror: src/darwin/api/contracts.py — Pydantic counterpart; keep field names and types in sync.

// ─── Gene layers ──────────────────────────────────────────────────────────────

export type EmbeddingModel = 'gemini_3072' | 'gemini_1536' | 'gemini_768' | 'gemini_256';
export type QueryTransform = 'none' | 'hyde' | 'multi_query' | 'step_back';
export type RerankStrategy = 'none' | 'cross_encoder' | 'llm_rerank' | 'reciprocal_rank_fusion';

export interface RetrievalGenes {
  embedding_model: EmbeddingModel;
  chunk_size: number; // tokens: 128 | 256 | 512 | 1024
  chunk_overlap: number; // fraction: 0.0 | 0.1 | 0.25 | 0.5
  query_transform: QueryTransform;
  rerank: RerankStrategy;
  confidence_threshold: number; // [0.0, 1.0]
  source_routing: string[];
}

export type CoordinationProtocol = 'solo' | 'vote' | 'consult' | 'debate';
export type DisagreementResolver = 'majority_vote' | 'highest_confidence' | 'debate';

export interface CoordinationGenes {
  protocol: CoordinationProtocol;
  consultation_count: number;
  disagreement_resolver: DisagreementResolver;
  timeout_ms: number;
}

export type MemoryStrategy = 'none' | 'checkpoint' | 'full_history';
export type ContextCompression = 'none' | 'summarize' | 'truncate';

export interface DurabilityGenes {
  memory_strategy: MemoryStrategy;
  checkpoint_every_n_turns: number;
  context_compression: ContextCompression;
}

// ─── Fitness ──────────────────────────────────────────────────────────────────

export interface FitnessComponents {
  relevance: number; // [0.0, 1.0]
  accuracy: number; // [0.0, 1.0]
  latency_ms: number;
  cost_usd: number;
}

export interface FitnessSummary {
  composite: number; // [0.0, 1.0]
  last_updated: string; // ISO 8601
}

// ─── Genome ───────────────────────────────────────────────────────────────────

export type GenomeStatus = 'alive' | 'retired';

export interface GenomeSummary {
  id: string;
  generation: number;
  status: GenomeStatus;
  fitness: FitnessSummary;
  retrieval_genes: RetrievalGenes;
  coordination_genes: CoordinationGenes;
  durability_genes: DurabilityGenes;
}

export interface GenomeDetail extends GenomeSummary {
  parent_ids: string[];
  created_at: string; // ISO 8601
  mutation_log: string[];
}

// ─── Retrieval trace ──────────────────────────────────────────────────────────

export interface RetrievalTraceItem {
  chunk_id: string;
  score: number;
  position: number;
}

// ─── Generation summary ───────────────────────────────────────────────────────

export interface GenerationRecord {
  generation: number;
  population_size: number;
  best_fitness: number;
  mean_fitness: number;
  diversity_index: number;
  selection: string;
  crossover_rate: number;
  mutation_rate: number;
  created_at: string; // ISO 8601
}

export interface FitnessCurvePoint {
  generation: number;
  best: number;
  mean: number;
  diversity: number;
}

// ─── API response wrappers ────────────────────────────────────────────────────

export interface FitnessCurveResponse {
  series: FitnessCurvePoint[];
}

export interface GenerationsResponse {
  generations: GenerationRecord[];
}

// ─── Lineage (/lineage/{genome_id}) ──────────────────────────────────────────

export interface LineageNode {
  id: string;
  generation: number;
  parent_ids: string[];
  fitness: FitnessSummary;
  retrieval_genes: RetrievalGenes;
  is_champion: boolean;
}

export interface LineageResponse {
  genome_id: string;
  nodes: LineageNode[];
}

// ─── Champions (/champions) ───────────────────────────────────────────────────

export interface ChampionRecord {
  id: string;
  original_genome_id: string;
  peak_fitness: number;
  generations_alive: number;
  lineage: string[]; // parent_id chain
  retired_at: string | null; // ISO 8601
  genome: GenomeSummary;
}

// ─── SSE events (/events) ─────────────────────────────────────────────────────

export type EvolutionEventType =
  | 'generation.evolved'
  | 'genome.born'
  | 'genome.retired'
  | 'champion.promoted'
  | 'query.completed';

export interface EvolutionEvent {
  event_type: EvolutionEventType;
  generation: number;
  data: Record<string, unknown>; // payload varies by event_type
  timestamp: string; // ISO 8601
}

// ─── Request / Response shapes ────────────────────────────────────────────────

export interface QueryRequest {
  text: string;
}

export interface QueryResponse {
  run_id: string;
  answer: string;
  winning_genome: GenomeSummary;
  fitness: FitnessComponents;
  composite_fitness: number;
  retrieval_trace: RetrievalTraceItem[];
}

export interface PopulationResponse {
  genomes: GenomeSummary[];
  generation: number;
  population_size: number;
}
