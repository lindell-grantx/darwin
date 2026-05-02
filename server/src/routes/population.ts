import { Hono } from 'hono';
import type { PopulationResponse } from '../../../src/contracts.ts';
import { genomes } from '../db/client.ts';
import { toGenomeSummary } from '../db/mappers.ts';

export const population = new Hono();

population.get('/', async (c) => {
  const docs = await genomes().find({ status: 'alive' }).toArray();
  const currentGeneration = docs.reduce((max, d) => Math.max(max, d.generation), 0);
  return c.json({
    current_generation: currentGeneration,
    alive_count: docs.length,
    genomes: docs.map(toGenomeSummary),
  } satisfies PopulationResponse);
});
