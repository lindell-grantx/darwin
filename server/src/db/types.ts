import type { ObjectId } from 'mongodb';
import type { FitnessComponentsAPI } from '../../../src/contracts.ts';

// Raw MongoDB document shapes — one interface per collection.
// IDs are ObjectId as stored; routes convert to .toHexString() for API responses.
// Re-use FitnessComponentsAPI from contracts rather than duplicating the shape.

export interface RetrievalGenes {
  embedding_model: 'gemini_3072' | 'gemini_1536' | 'gemini_768' | 'gemini_256';
  chunk_size: 128 | 256 | 512 | 1024;
  chunk_overlap: 0.0 | 0.1 | 0.25 | 0.5;
  query_transform: 'none' | 'hyde' | 'multi_query' | 'step_back';
  rerank: 'none' | 'cross_encoder' | 'llm_rerank' | 'reciprocal_rank_fusion';
  confidence_threshold: number;
  source_routing: string[];
}

export interface CoordinationGenes {
  protocol: 'solo' | 'vote' | 'consult' | 'debate';
  consultation_count: number;
  disagreement_resolver: 'majority_vote' | 'highest_confidence' | 'debate';
  timeout_ms: number;
}

export interface DurabilityGenes {
  memory_strategy: 'none' | 'checkpoint' | 'full_history';
  checkpoint_every_n_turns: number;
  context_compression: 'none' | 'summarize' | 'truncate';
}

export interface FitnessDoc {
  composite: number;
  last_updated: Date;
}

// ── genomes ──────────────────────────────────────────────────────────────────

export interface GenomeDoc {
  _id: ObjectId;
  generation: number;
  status: 'alive' | 'retired';
  parent_ids: ObjectId[];
  retrieval_genes: RetrievalGenes;
  coordination_genes: CoordinationGenes;
  durability_genes: DurabilityGenes;
  fitness: FitnessDoc;
  mutation_log: string[];
  created_at: Date;
}

// ── generations ───────────────────────────────────────────────────────────────

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
  created_at: Date;
}

// ── queries ───────────────────────────────────────────────────────────────────

export interface QueryDoc {
  _id: ObjectId;
  text: string;
  expected_facts: string[];
  tag: string;
  created_at: Date;
}

// ── fitness_evaluations ───────────────────────────────────────────────────────

export type { FitnessComponentsAPI };

export interface RetrievalTraceEntry {
  chunk_id: ObjectId;
  score: number;
  position: number;
}

export interface FitnessEvaluationDoc {
  _id: ObjectId;
  genome_id: ObjectId;
  query_id: ObjectId;
  generation: number;
  run_id: string;
  generated_answer: string;
  retrieval_trace: RetrievalTraceEntry[];
  coordination_trace: Record<string, unknown>;
  components: FitnessComponentsAPI;
  composite_fitness: number;
  timestamp: Date;
}

// ── chunks ────────────────────────────────────────────────────────────────────

export interface ChunkDoc {
  _id: ObjectId;
  text: string;
  source: string;
  url: string;
  tag: string;
  chunk_index: number;
  embeddings: {
    gemini_3072?: number[];
    gemini_1536?: number[];
    gemini_768?: number[];
    gemini_256?: number[];
  };
  created_at: Date;
}

// ── champions ─────────────────────────────────────────────────────────────────

export interface ChampionDoc {
  _id: ObjectId;
  original_genome_id: ObjectId;
  peak_fitness: number;
  generations_alive: number;
  lineage: ObjectId[];
  retired_at: Date | null;
  promoted_at: Date;
  genome: GenomeDoc;
}
