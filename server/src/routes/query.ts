import { Hono } from 'hono';
import type {
  CoordinationGenes,
  FitnessComponents,
  GenerationGenes,
  GenomeStatus,
  GenomeSummary,
  QueryRequest,
  QueryResponse,
  RetrievalGenes,
  RetrievalTraceItem,
} from '../../../src/contracts.ts';
import { env } from '../env.ts';

export const query = new Hono();

const EVALUATE_TIMEOUT_MS = 60_000;

// Python /evaluate response shape — winning_genome has composite_fitness as a
// direct field rather than the nested fitness object the contract uses.
interface PyEvaluateGenome {
  id: string;
  generation: number;
  status: GenomeStatus;
  composite_fitness: number;
  retrieval_genes: RetrievalGenes;
  coordination_genes: CoordinationGenes;
  generation_genes: GenerationGenes;
}

interface PyEvaluateResponse {
  run_id: string;
  answer: string;
  winning_genome: PyEvaluateGenome;
  composite_fitness: number;
  fitness: FitnessComponents;
  retrieval_trace: RetrievalTraceItem[];
  rationale?: string;
  timestamp?: string;
}

// Use the run's score for the genome card so the UI shows what was just
// evaluated, not the genome's stale stored aggregate (which can be 0 for
// a fresh genome that's never been evaluated before this query).
function toGenomeSummary(g: PyEvaluateGenome, runFitness: number): GenomeSummary {
  return {
    id: g.id,
    generation: g.generation,
    status: g.status,
    fitness: {
      composite: runFitness,
      n_evaluations: 1,
      last_updated: new Date().toISOString(),
    },
    retrieval_genes: g.retrieval_genes,
    coordination_genes: g.coordination_genes,
    generation_genes: g.generation_genes,
  };
}

query.post('/', async (c) => {
  const body = await c.req.json<QueryRequest>();

  if (!body.text?.trim()) {
    return c.json({ error: 'empty_query' }, 400);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), EVALUATE_TIMEOUT_MS);

  try {
    const response = await fetch(`${env.PYTHON_SERVICE_URL}/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: body.text,
        genome_id: null,
        persist: true,
      }),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      throw new Error(`Python service returned ${response.status}: ${errorText}`);
    }

    const result = (await response.json()) as PyEvaluateResponse;

    const queryResponse: QueryResponse = {
      run_id: result.run_id,
      answer: result.answer,
      winning_genome: toGenomeSummary(result.winning_genome, result.composite_fitness),
      fitness: result.fitness,
      composite_fitness: result.composite_fitness,
      retrieval_trace: result.retrieval_trace,
    };

    return c.json(queryResponse);
  } catch (error) {
    const isAbort = error instanceof Error && error.name === 'AbortError';
    console.error('[POST /query] evaluation failed:', error);
    return c.json(
      {
        error: isAbort ? 'evaluation_timeout' : 'evaluation_failed',
        message: error instanceof Error ? error.message : String(error),
      },
      isAbort ? 504 : 502,
    );
  } finally {
    clearTimeout(timeoutId);
  }
});
