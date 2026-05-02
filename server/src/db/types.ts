import type { ObjectId } from 'mongodb';
import type {
  CoordinationGenes,
  FitnessComponents,
  GenerationGenes,
  GenomeStatus,
  RetrievalGenes,
} from '../../../src/contracts.ts';

// Raw MongoDB document shapes — mirror the live Atlas schema.
// Most ids are UUID strings (not ObjectId). The `generations` timeseries
// collection is the exception — it uses a Mongo-managed ObjectId on _id.

// ── genomes ──────────────────────────────────────────────────────────────────

export interface FitnessDoc {
  composite: number;
  n_evaluations: number;
  last_updated: Date | null;
}

export interface GenomeDoc {
  _id: string;
  generation: number;
  status: GenomeStatus;
  parent_ids: string[];
  retrieval_genes: RetrievalGenes;
  coordination_genes: CoordinationGenes;
  generation_genes: GenerationGenes;
  fitness: FitnessDoc;
  created_at: Date;
  notes: string | null;
}

// ── generations (timeseries) ──────────────────────────────────────────────────

export interface GenerationDoc {
  _id: ObjectId;
  generation: number;
  population_size: number;
  best_fitness: number;
  mean_fitness: number;
  diversity_index: number;
  selection: string;
  crossover_rate: number;
  mutation_rate: number;
  elite_genome_ids: string[];
  created_at: Date;
}

// ── queries ───────────────────────────────────────────────────────────────────

export interface QueryDoc {
  _id: string;
  text: string;
  expected_facts: string[];
  ground_truth: string;
  difficulty: string;
  domain_tags: string[];
  seeded: boolean;
  created_at: Date;
  updated_at: Date;
}

// ── fitness_evaluations ───────────────────────────────────────────────────────

export type { FitnessComponents };

export interface RetrievalTraceEntry {
  chunk_id: string;
  score: number;
  position: number;
}

export interface FitnessEvaluationDoc {
  _id: string;
  genome_id: string;
  query_id: string;
  generation: number;
  run_id: string;
  generated_answer: string;
  retrieval_trace: RetrievalTraceEntry[];
  coordination_trace: Record<string, unknown>;
  components: FitnessComponents;
  composite_fitness: number;
  eval_split?: 'train' | 'holdout';
}

// ── chunks ────────────────────────────────────────────────────────────────────

export interface ChunkDoc {
  _id: string;
  text: string;
  source: string;
  url: string;
  tag: string;
  chunk_index: number;
  embeddings: Record<string, number[]>;
  created_at: Date;
}

// ── champions ─────────────────────────────────────────────────────────────────

export interface ChampionDoc {
  _id: string;
  genome_id: string;
  promoted_at_generation: number;
  composite_fitness: number;
  summary: string | null;
  created_at: Date;
}

// ── query_runs (Hono → Python bridge) ─────────────────────────────────────────

export type QueryRunStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface QueryRunDoc {
  _id: string;
  text: string;
  status: QueryRunStatus;
  requested_at: Date;
  started_at: Date | null;
  completed_at: Date | null;
  target_genome_id: string | null;
  evaluation_id: string | null;
  error: string | null;
}

// ── evolution_events (Python → Hono bridge) ──────────────────────────────────
// Mirrors what would otherwise be a generations-collection change stream
// (which Mongo doesn't allow on time-series collections).

export type EvolutionEventDocType =
  | 'generation.evolved'
  | 'champion.promoted'
  | 'population.seeded';

export interface EvolutionEventDoc {
  _id: string;
  event_type: EvolutionEventDocType;
  generation: number;
  payload: Record<string, unknown>;
  created_at: Date;
}
