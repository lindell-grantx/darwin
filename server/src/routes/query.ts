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

// Python /evaluate response shape — winning_genome has composite_fitness as a
// direct field, not nested in a fitness object like our contract expects.
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

function toGenomeSummary(g: PyEvaluateGenome): GenomeSummary {
  return {
    id: g.id,
    generation: g.generation,
    status: g.status,
    fitness: {
      composite: g.composite_fitness,
      n_evaluations: 0,
      last_updated: null,
    },
    retrieval_genes: g.retrieval_genes,
    coordination_genes: g.coordination_genes,
    generation_genes: g.generation_genes,
  };
}

// POST /query — proxies to external Python evaluation service
query.post('/', async (c) => {
  const body = await c.req.json<QueryRequest>();

  if (!body.text?.trim()) {
    return c.json({ error: 'empty_query' }, 400);
  }

  try {
    const response = await fetch(`${env.PYTHON_SERVICE_URL}/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: body.text,
        genome_id: null,
        persist: true,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      throw new Error(`Python service returned ${response.status}: ${errorText}`);
    }

    const result = (await response.json()) as PyEvaluateResponse;

    const queryResponse: QueryResponse = {
      run_id: result.run_id,
      answer: result.answer,
      winning_genome: toGenomeSummary(result.winning_genome),
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
