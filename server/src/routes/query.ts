import { Hono } from 'hono';
import type { QueryRequest, QueryResponse } from '../../../src/contracts.ts';
import { mockQueryResponse } from '../db/mock.ts';

export const query = new Hono();

// POST /query — submit a query, run the population on it, return result.
// TODO(stream-c): tournament-select genomes, fanout to agent_runner, judge fitness.
// For now: return mock response so the UI is exercisable end-to-end.
query.post('/', async (c) => {
  const body = await c.req.json<QueryRequest>();
  await new Promise((r) => setTimeout(r, 700));
  const response: QueryResponse = mockQueryResponse(body.text ?? '');
  return c.json(response);
});
