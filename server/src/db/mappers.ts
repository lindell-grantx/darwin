import type { GenomeSummary } from '../../../src/contracts.ts';
import type { GenomeDoc } from './types.ts';

export function toGenomeSummary(doc: GenomeDoc): GenomeSummary {
  return {
    id: doc._id.toHexString(),
    generation: doc.generation,
    retrieval_genes: doc.retrieval_genes as unknown as Record<string, unknown>,
    coordination_genes: doc.coordination_genes as unknown as Record<string, unknown>,
    durability_genes: doc.durability_genes as unknown as Record<string, unknown>,
    fitness_composite: doc.fitness.composite,
  };
}

export function computeGeneDiff(
  parent: GenomeDoc,
  child: GenomeDoc,
): Record<string, [unknown, unknown]> {
  const diff: Record<string, [unknown, unknown]> = {};
  const layers = ['retrieval_genes', 'coordination_genes', 'durability_genes'] as const;
  for (const layer of layers) {
    const p = parent[layer] as unknown as Record<string, unknown>;
    const c = child[layer] as unknown as Record<string, unknown>;
    for (const key of Object.keys(p)) {
      if (JSON.stringify(p[key]) !== JSON.stringify(c[key])) {
        diff[`${layer}.${key}`] = [p[key], c[key]];
      }
    }
  }
  return diff;
}
