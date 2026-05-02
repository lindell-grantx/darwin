import { Hono } from 'hono';
import type { QueryRequest, QueryResponse } from '../../../src/contracts.ts';
import { fitnessEvaluations, genomes } from '../db/client.ts';
import { idToString, toGenomeSummary } from '../db/mappers.ts';

export const query = new Hono();

// POST /query — currently returns a snapshot grounded in real DB state:
// the best-fitness genome alive, plus a recent fitness evaluation for it.
// TODO(stream-c): replace with real tournament-select + agent-runner + judge.
query.post('/', async (c) => {
  const body = await c.req.json<QueryRequest>();

  const winner = await genomes().findOne(
    { status: { $in: ['alive', 'champion'] } },
    { sort: { 'fitness.composite': -1 } },
  );
  if (!winner) return c.json({ error: 'no_population' }, 503);

  const recentEval = await fitnessEvaluations().findOne(
    { genome_id: idToString(winner._id) },
    { sort: { generation: -1 } },
  );

  const response: QueryResponse = {
    run_id: `run_${Date.now()}`,
    answer: recentEval?.generated_answer ?? `[no evaluation yet] received: ${body.text ?? ''}`,
    winning_genome: toGenomeSummary(winner),
    fitness: recentEval?.components ?? {
      relevance: 0,
      accuracy: 0,
      coverage: 0,
      latency_ms: 0,
      cost_usd: 0,
    },
    composite_fitness: recentEval?.composite_fitness ?? winner.fitness.composite,
    retrieval_trace: (recentEval?.retrieval_trace ?? []).map((t) => ({
      chunk_id: idToString(t.chunk_id),
      score: t.score,
      position: t.position,
    })),
  };
  return c.json(response);
});
