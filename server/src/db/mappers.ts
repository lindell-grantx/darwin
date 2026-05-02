import type { ChampionRecord, GenerationRecord, GenomeSummary } from '../../../src/contracts.ts';
import type { ChampionDoc, GenerationDoc, GenomeDoc } from './types.ts';

// Some collections store _id as a UUID string; others (like generations)
// use Mongo-managed ObjectIds. Normalise both.
export function idToString(id: unknown): string {
  if (typeof id === 'string') return id;
  if (
    id &&
    typeof id === 'object' &&
    'toHexString' in id &&
    typeof (id as { toHexString: unknown }).toHexString === 'function'
  ) {
    return (id as { toHexString: () => string }).toHexString();
  }
  return String(id);
}

// Dates may be a BSON Date (the common case), an ISO string (legacy seeds),
// or null (e.g. fitness.last_updated for never-evaluated genomes).
export function toIso(v: unknown): string | null {
  if (v == null) return null;
  if (v instanceof Date) return v.toISOString();
  if (typeof v === 'string') return v;
  return null;
}

export function toGenomeSummary(doc: GenomeDoc): GenomeSummary {
  return {
    id: idToString(doc._id),
    generation: doc.generation,
    status: doc.status,
    fitness: {
      composite: doc.fitness.composite,
      n_evaluations: doc.fitness.n_evaluations,
      last_updated: toIso(doc.fitness.last_updated),
    },
    retrieval_genes: doc.retrieval_genes,
    coordination_genes: doc.coordination_genes,
    generation_genes: doc.generation_genes,
  };
}

export function toGenerationRecord(doc: GenerationDoc): GenerationRecord {
  return {
    generation: doc.generation,
    population_size: doc.population_size,
    best_fitness: doc.best_fitness,
    mean_fitness: doc.mean_fitness,
    diversity_index: doc.diversity_index,
    selection: doc.selection,
    crossover_rate: doc.crossover_rate,
    mutation_rate: doc.mutation_rate,
    created_at: toIso(doc.created_at) ?? new Date(0).toISOString(),
    elite_genome_ids: (doc.elite_genome_ids ?? []).map(idToString),
  };
}

export function toChampionRecord(doc: ChampionDoc): ChampionRecord {
  return {
    id: idToString(doc._id),
    genome_id: idToString(doc.genome_id),
    promoted_at_generation: doc.promoted_at_generation,
    composite_fitness: doc.composite_fitness,
    summary: doc.summary,
    created_at: toIso(doc.created_at) ?? new Date(0).toISOString(),
  };
}
