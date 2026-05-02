// Canonical API ↔ UI contracts.
// Imported by both the Hono server (server/src/) and the Vite UI (frontend/src/ via @contracts alias).
// Source of truth: the live MongoDB Atlas schema. See server/src/db/types.ts for raw doc shapes.

// ─── Gene layers ──────────────────────────────────────────────────────────────

export type EmbeddingModel = 'voyage-4-lite' | 'voyage-4' | 'voyage-4-large' | 'voyage-code-3';
export type QueryTransform = 'none' | 'hyde' | 'multi_query' | 'step_back';
export type RerankStrategy = 'none' | 'rrf' | 'voyage-rerank-2';
export type SourceTag = 'mongodb' | 'langchain' | 'voyage';

export interface RetrievalGenes {
  embedding_model: EmbeddingModel;
  chunk_size: number; // tokens: 128 | 256 | 512 | 1024
  chunk_overlap: number; // fraction in [0.0, 1.0]
  query_transform: QueryTransform;
  rerank: RerankStrategy;
  confidence_threshold: number; // [0.0, 1.0]
  top_k: number;
  source_routing: SourceTag[];
}

export type CoordinationProtocol = 'solo' | 'vote' | 'consult' | 'debate';

export interface CoordinationGenes {
  protocol: CoordinationProtocol;
  consult_threshold: number; // [0.0, 1.0]
  timeout_ms: number;
  debate_rounds: number;
}

export type GenerationModel = 'claude-haiku-4-5-20251001' | 'claude-sonnet-4-6';
export type SystemStyle = 'detailed' | 'stepwise' | 'concise';

export interface GenerationGenes {
  model: GenerationModel;
  temperature: number;
  max_tokens: number;
  system_style: SystemStyle;
}

// ─── Fitness ──────────────────────────────────────────────────────────────────

export interface FitnessComponents {
  relevance: number; // [0.0, 1.0]
  accuracy: number; // [0.0, 1.0]
  coverage: number; // [0.0, 1.0]
  latency_ms: number;
  cost_usd: number;
}

export interface FitnessSummary {
  composite: number; // [0.0, 1.0]
  n_evaluations: number;
  last_updated: string | null; // ISO 8601, null if never evaluated
}

// ─── Genome ───────────────────────────────────────────────────────────────────

export type GenomeStatus = 'alive' | 'retired' | 'champion';

export interface GenomeSummary {
  id: string;
  generation: number;
  status: GenomeStatus;
  fitness: FitnessSummary;
  retrieval_genes: RetrievalGenes;
  coordination_genes: CoordinationGenes;
  generation_genes: GenerationGenes;
}

export interface GenomeDetail extends GenomeSummary {
  parent_ids: string[];
  created_at: string; // ISO 8601
  notes: string | null;
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
  elite_genome_ids: string[];
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
  genome_id: string;
  promoted_at_generation: number;
  composite_fitness: number;
  summary: string | null;
  created_at: string; // ISO 8601
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
