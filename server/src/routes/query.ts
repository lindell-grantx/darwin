import { Hono } from 'hono';
import type { QueryRequest, QueryResponse } from '../../../src/contracts.ts';
import { env } from '../env.ts';

export const query = new Hono();

// POST /query — proxies to external Python evaluation service
query.post('/', async (c) => {
  const body = await c.req.json<QueryRequest>();

  if (!body.text?.trim()) {
    return c.json({ error: 'empty_query' }, 400);
  }

  try {
    // Call external Python evaluation service
    const response = await fetch(`${env.PYTHON_SERVICE_URL}/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: body.text,
        genome_id: null, // Let Python pick best genome
        persist: true, // Save evaluation to fitness_evaluations
      }),
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      throw new Error(`Python service returned ${response.status}: ${errorText}`);
    }

    const result = (await response.json()) as QueryResponse;

    // Map external response to QueryResponse contract (response already matches)
    const queryResponse: QueryResponse = {
      run_id: result.run_id,
      answer: result.answer,
      winning_genome: result.winning_genome,
      fitness: result.fitness,
      composite_fitness: result.composite_fitness,
      retrieval_trace: result.retrieval_trace,
    };

    return c.json(queryResponse);
  } catch (error) {
    console.error('[POST /query] evaluation failed:', error);
    return c.json(
      {
        error: 'evaluation_failed',
        message: error instanceof Error ? error.message : String(error),
      },
      502,
    );
  }
});
