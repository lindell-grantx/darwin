import type { GenomeSummary } from '../../../src/contracts.ts';
import type { GenomeDoc } from './types.ts';

// Some docs were seeded with string _id instead of ObjectId; normalise both.
export function idToString(id: unknown): string {
  if (typeof id === 'string') return id;
  if (id && typeof id === 'object' && 'toHexString' in id && typeof (id as { toHexString: unknown }).toHexString === 'function') {
    return (id as { toHexString: () => string }).toHexString();
  }
  return String(id);
}

// Upstream writers occasionally produce docs with null/missing date fields;
// fall back to epoch so a single bad doc doesn't poison the whole response.
export function toIsoString(d: Date | null | undefined): string {
  return d instanceof Date ? d.toISOString() : new Date(0).toISOString();
}

export function toGenomeSummary(doc: GenomeDoc): GenomeSummary {
  return {
    id: idToString(doc._id),
    generation: doc.generation,
    status: doc.status,
    fitness: {
      composite: doc.fitness?.composite ?? 0,
      last_updated: toIsoString(doc.fitness?.last_updated),
    },
    retrieval_genes: doc.retrieval_genes,
    coordination_genes: doc.coordination_genes,
    durability_genes: doc.durability_genes,
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
