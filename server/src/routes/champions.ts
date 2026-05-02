import { Hono } from 'hono';
import type { ChampionRecord } from '../../../src/contracts.ts';
import { champions as championsCol } from '../db/client.ts';
import { toGenomeSummary } from '../db/mappers.ts';
import { mockChampions, withMock } from '../db/mock.ts';

export const champions = new Hono();

champions.get('/', async (c) => {
  const data = await withMock<ChampionRecord[]>(async () => {
    const docs = await championsCol().find().sort({ peak_fitness: -1 }).toArray();
    if (docs.length === 0) return null;
    return docs.map((d) => ({
      id: d._id.toHexString(),
      original_genome_id: d.original_genome_id.toHexString(),
      peak_fitness: d.peak_fitness,
      generations_alive: d.generations_alive,
      lineage: d.lineage.map((id) => id.toHexString()),
      retired_at: d.retired_at?.toISOString() ?? null,
      genome: toGenomeSummary(d.genome),
    }));
  }, mockChampions);
  return c.json(data);
});
