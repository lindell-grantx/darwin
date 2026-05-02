import { Hono } from 'hono';
import type { GenerationsResponse } from '../../../src/contracts.ts';
import { generations as generationsCol } from '../db/client.ts';
import { mockGenerations, withMock } from '../db/mock.ts';

export const generations = new Hono();

generations.get('/', async (c) => {
  const data = await withMock<GenerationsResponse>(async () => {
    const docs = await generationsCol().find().sort({ generation: 1 }).toArray();
    if (docs.length === 0) return null;
    return {
      generations: docs.map((d) => ({
        generation: d.generation,
        created_at: d.created_at.toISOString(),
        population_size: d.population_size,
        best_fitness: d.best_fitness,
        mean_fitness: d.mean_fitness,
        diversity_index: d.diversity_index,
      })),
    };
  }, mockGenerations);
  return c.json(data);
});
