import { Hono } from 'hono';
import { ping } from '../db/client.ts';

export const health = new Hono();

health.get('/', async (c) => {
  let db: 'ok' | 'error' = 'ok';
  try {
    await ping();
  } catch {
    db = 'error';
  }
  const status = db === 'ok' ? 200 : 503;
  return c.json({ ok: db === 'ok', service: 'darwin', db, ts: new Date().toISOString() }, status);
});
