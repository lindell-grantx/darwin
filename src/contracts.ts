// Canonical API ↔ UI contracts (DAR-17).
// Imported by both the Hono server (src/server.ts) and the Vite UI
// (ui/ — via the `@contracts` alias in vite.config.ts and tsconfig.json).
//
// Any change here is automatically reflected on both sides — no mirroring needed
// since the whole stack is TypeScript.

// ─── Genome / fitness primitives ─────────────────────────────────────────────

export interface GenomeSummary {
  id: string;
  generation: number;
  retrieval_genes: Record<string, unknown>;
  coordination_genes: Record<string, unknown>;
  durability_genes: Record<string, unknown>;
  fitness_composite: number;
}

export interface FitnessComponentsAPI {
  relevance: number;
  accuracy: number;
  coverage: number;
  latency_ms: number;
  cost_usd: number;
}

export interface RetrievalTraceItem {
  chunk_id: string;
  score: number;
  position: number;
}

export interface GenomeRunResult {
  genome_id: string;
  answer: string;
  fitness: FitnessComponentsAPI;
  composite_fitness: number;
  retrieval_trace: RetrievalTraceItem[];
}

// ─── Endpoint request / response shapes ──────────────────────────────────────

// POST /query
export interface QueryRequest {
  text: string;
}

export interface QueryResponse {
  run_id: string;
  answer: string;
  winning_genome: GenomeSummary;
  all_genome_results: GenomeRunResult[];
  fitness: FitnessComponentsAPI;
  latency_ms: number;
}

// GET /population
export interface PopulationResponse {
  current_generation: number;
  alive_count: number;
  genomes: GenomeSummary[];
}

// GET /generations
export interface GenerationSummary {
  generation: number;
  created_at: string; // ISO 8601
  population_size: number;
  best_fitness: number;
  mean_fitness: number;
  diversity_index: number;
}

export interface GenerationsResponse {
  generations: GenerationSummary[];
}

// GET /fitness-curve
export interface FitnessCurvePoint {
  generation: number;
  best: number;
  mean: number;
  diversity: number;
}

export interface FitnessCurveResponse {
  series: FitnessCurvePoint[];
}

// GET /lineage/:genomeId
export interface LineageNode {
  genome: GenomeSummary;
  gene_diff: Record<string, [unknown, unknown]>; // {field_path: [parent_value, child_value]}
  depth: number;
}

export interface LineageResponse {
  genome: GenomeSummary;
  ancestors: LineageNode[];
}

// GET /champions
export interface Champion {
  id: string;
  original_genome_id: string;
  peak_fitness: number;
  generations_alive: number;
  lineage: string[]; // parent ids
  retired_at: string; // ISO 8601
  final_genes: Record<string, unknown>;
  current_genome?: GenomeSummary;
}

// ─── SSE events (GET /events) ────────────────────────────────────────────────

export type EvolutionEventType =
  | 'evaluation.created'
  | 'generation.evolved'
  | 'champion.promoted'
  | 'query.started'
  | 'query.completed';

interface EvolutionEventBase<T extends EvolutionEventType, D> {
  type: T;
  timestamp: string; // ISO 8601
  data: D;
}

export type EvaluationCreatedEvent = EvolutionEventBase<
  'evaluation.created',
  {
    genome_id: string;
    query_id: string;
    composite_fitness: number;
    generation: number;
  }
>;

export type GenerationEvolvedEvent = EvolutionEventBase<
  'generation.evolved',
  {
    generation: number;
    best_fitness: number;
    mean_fitness: number;
    n_offspring: number;
  }
>;

export type ChampionPromotedEvent = EvolutionEventBase<
  'champion.promoted',
  {
    champion_id: string;
    original_genome_id: string;
    peak_fitness: number;
  }
>;

export type QueryStartedEvent = EvolutionEventBase<
  'query.started',
  {
    run_id: string;
    query_text: string;
    n_genomes: number;
  }
>;

export type QueryCompletedEvent = EvolutionEventBase<
  'query.completed',
  {
    run_id: string;
    winning_genome_id: string;
  }
>;

export type EvolutionEvent =
  | EvaluationCreatedEvent
  | GenerationEvolvedEvent
  | ChampionPromotedEvent
  | QueryStartedEvent
  | QueryCompletedEvent;
