import { Hono } from 'hono';

export const population = new Hono();

// GET /population — list of alive genomes with summary fitness
population.get('/', async (c) => {
  // TODO(stream-b): db.genomes.find({ status: 'alive' }) with fitness summary
  return c.json({ genomes: [] });
});
