import { Hono } from 'hono';

export const generations = new Hono();

// GET /generations — time-series of generation summaries
generations.get('/', async (c) => {
  // TODO(stream-b): db.generations time-series read
  return c.json({ generations: [] });
});
