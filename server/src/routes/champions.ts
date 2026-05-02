import { Hono } from 'hono';

export const champions = new Hono();

// GET /champions — hall of fame
champions.get('/', async (c) => {
  // TODO(stream-b): db.champions sorted by fitness desc
  return c.json({ champions: [] });
});
