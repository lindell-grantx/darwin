import { Hono } from 'hono';

export const query = new Hono();

// POST /query — submit a query, run the population on it, return result
query.post('/', async (c) => {
  const body = await c.req.json<{ text: string }>();
  // TODO(stream-c): tournament-select genomes, fanout to agent_runner, await results
  return c.json(
    {
      run_id: crypto.randomUUID(),
      text: body.text,
      answer: null,
      winning_genome: null,
      fitness: null,
    },
    501,
  );
});
