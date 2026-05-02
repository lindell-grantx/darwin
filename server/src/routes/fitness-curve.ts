import { Hono } from 'hono';

export const fitnessCurve = new Hono();

// GET /fitness-curve — [{ generation, best, mean, diversity }, ...]
fitnessCurve.get('/', async (c) => {
  // TODO(stream-b): aggregation pipeline over fitness_evaluations + generations
  return c.json({ points: [] });
});
