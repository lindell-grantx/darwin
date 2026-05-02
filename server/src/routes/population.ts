import { Hono } from 'hono';
import type { PopulationResponse } from '../../../src/contracts.ts';
import { genomes } from '../db/client.ts';
import { toGenomeSummary } from '../db/mappers.ts';
import { mockPopulation, withMock } from '../db/mock.ts';

export const population = new Hono();

population.get('/', async (c) => {
  const data = await withMock<PopulationResponse>(async () => {
    const docs = await genomes().find({ status: 'alive' }).toArray();
    if (docs.length === 0) return null;
    const currentGeneration = docs.reduce((max, d) => Math.max(max, d.generation), 0);
    return {
      current_generation: currentGeneration,
      alive_count: docs.length,
      genomes: docs.map(toGenomeSummary),
    };
  }, mockPopulation);
  return c.json(data);
});
