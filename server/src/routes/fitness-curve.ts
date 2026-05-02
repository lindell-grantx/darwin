import { Hono } from 'hono';
import type { FitnessCurveResponse } from '../../../src/contracts.ts';
import { generations } from '../db/client.ts';

export const fitnessCurve = new Hono();

fitnessCurve.get('/', async (c) => {
  const docs = await generations().find().sort({ generation: 1 }).toArray();
  const response: FitnessCurveResponse = {
    series: docs.map((d) => ({
      generation: d.generation,
      best: d.best_fitness,
      mean: d.mean_fitness,
      diversity: d.diversity_index,
    })),
  };
  return c.json(response);
});
