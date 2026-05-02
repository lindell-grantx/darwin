import { Hono } from 'hono';
import type { FitnessCurveResponse } from '../../../src/contracts.ts';
import { generations } from '../db/client.ts';
import { mockFitnessCurve, withMock } from '../db/mock.ts';

export const fitnessCurve = new Hono();

fitnessCurve.get('/', async (c) => {
  const data = await withMock<FitnessCurveResponse>(async () => {
    const docs = await generations().find().sort({ generation: 1 }).toArray();
    if (docs.length === 0) return null;
    return {
      series: docs.map((d) => ({
        generation: d.generation,
        best: d.best_fitness,
        mean: d.mean_fitness,
        diversity: d.diversity_index,
      })),
    };
  }, mockFitnessCurve);
  return c.json(data);
});
