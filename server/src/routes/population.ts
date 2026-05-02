import { Hono } from 'hono';
import type { PopulationResponse } from '../../../src/contracts.ts';
import { genomes } from '../db/client.ts';
import { toGenomeSummary } from '../db/mappers.ts';

export const population = new Hono();

// Current population = all non-retired genomes (alive + champion).
population.get('/', async (c) => {
  const docs = await genomes()
    .find({ status: { $in: ['alive', 'champion'] } })
    .sort({ 'fitness.composite': -1 })
    .toArray();

  const currentGeneration = docs.reduce((max, d) => Math.max(max, d.generation), 0);
  const response: PopulationResponse = {
    generation: currentGeneration,
    population_size: docs.length,
    genomes: docs.map(toGenomeSummary),
  };
  return c.json(response);
});
