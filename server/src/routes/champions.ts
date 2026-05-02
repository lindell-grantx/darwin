import { Hono } from 'hono';
import { champions as championsCol } from '../db/client.ts';
import { toGenomeSummary } from '../db/mappers.ts';

export const champions = new Hono();

champions.get('/', async (c) => {
  const docs = await championsCol().find().sort({ peak_fitness: -1 }).toArray();
  return c.json({
    champions: docs.map((d) => ({
      id: d._id.toHexString(),
      original_genome_id: d.original_genome_id.toHexString(),
      peak_fitness: d.peak_fitness,
      generations_alive: d.generations_alive,
      lineage: d.lineage.map((id) => id.toHexString()),
      retired_at: d.retired_at?.toISOString() ?? '',
      final_genes: {
        ...d.genome.retrieval_genes,
        ...d.genome.coordination_genes,
        ...d.genome.durability_genes,
      } as Record<string, unknown>,
      current_genome: toGenomeSummary(d.genome),
    })),
  });
});
