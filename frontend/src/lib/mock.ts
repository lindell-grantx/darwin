import type {
  Champion,
  EvolutionEvent,
  FitnessCurveResponse,
  GenomeSummary,
  LineageResponse,
  PopulationResponse,
  QueryResponse,
} from '@contracts';

const genome = (id: string, generation: number, fitness: number): GenomeSummary => ({
  id,
  generation,
  retrieval_genes: { embedder: 'voyage-3', k: 5 + generation, rerank: true },
  coordination_genes: { quorum: 2, voters: ['claude', 'voyage'] },
  durability_genes: { ttl_s: 600, replay_quorum: 2 },
  fitness_composite: fitness,
});

const POP: GenomeSummary[] = [
  genome('g0_a', 0, 0.41),
  genome('g0_b', 0, 0.38),
  genome('g1_a', 1, 0.52),
  genome('g1_b', 1, 0.49),
  genome('g2_a', 2, 0.61),
  genome('g2_b', 2, 0.58),
  genome('g3_a', 3, 0.71),
  genome('g3_b', 3, 0.67),
  genome('g4_a', 4, 0.78),
];

export const mockFitnessCurve: FitnessCurveResponse = {
  series: [
    { generation: 0, best: 0.41, mean: 0.32, diversity: 0.81 },
    { generation: 1, best: 0.52, mean: 0.44, diversity: 0.74 },
    { generation: 2, best: 0.61, mean: 0.51, diversity: 0.69 },
    { generation: 3, best: 0.71, mean: 0.6, diversity: 0.62 },
    { generation: 4, best: 0.78, mean: 0.66, diversity: 0.55 },
  ],
};

export const mockPopulation: PopulationResponse = {
  current_generation: 4,
  alive_count: POP.length,
  genomes: POP,
};

const LINEAGE_PARENTS: Record<string, string | undefined> = {
  g0_a: undefined,
  g0_b: undefined,
  g1_a: 'g0_a',
  g1_b: 'g0_b',
  g2_a: 'g1_a',
  g2_b: 'g1_b',
  g3_a: 'g2_a',
  g3_b: 'g2_b',
  g4_a: 'g3_a',
};

export function mockLineage(genomeId: string): LineageResponse {
  const target = POP.find((g) => g.id === genomeId) ?? POP[POP.length - 1]!;
  const ancestors: LineageResponse['ancestors'] = [];
  let cur: string | undefined = LINEAGE_PARENTS[target.id];
  let depth = 1;
  while (cur) {
    const g = POP.find((p) => p.id === cur);
    if (!g) break;
    ancestors.push({
      genome: g,
      gene_diff: { 'retrieval_genes.k': [g.retrieval_genes.k, (g.retrieval_genes.k as number) + 1] },
      depth,
    });
    cur = LINEAGE_PARENTS[cur];
    depth += 1;
  }
  return { genome: target, ancestors };
}

export const mockChampions: Champion[] = [
  {
    id: 'champ_001',
    original_genome_id: 'g3_a',
    peak_fitness: 0.74,
    generations_alive: 3,
    lineage: ['g0_a', 'g1_a', 'g2_a', 'g3_a'],
    retired_at: new Date(Date.now() - 1000 * 60 * 8).toISOString(),
    final_genes: { embedder: 'voyage-3', k: 8, rerank: true },
    current_genome: POP.find((g) => g.id === 'g3_a'),
  },
];

export const mockQueryResponse: QueryResponse = {
  run_id: 'run_demo_001',
  answer:
    'MongoDB Atlas Vector Search uses HNSW indexes by default. For 1M+ vectors at scale, tune `numCandidates` ≥ 10× `limit` and prefer cosine similarity for normalized embeddings.',
  winning_genome: POP[POP.length - 1]!,
  all_genome_results: POP.slice(-3).map((g) => ({
    genome_id: g.id,
    answer: `Answer from ${g.id} (composite fitness ${g.fitness_composite.toFixed(2)})`,
    fitness: {
      relevance: 0.78 + Math.random() * 0.1,
      accuracy: 0.81 + Math.random() * 0.08,
      coverage: 0.65 + Math.random() * 0.15,
      latency_ms: 800 + Math.random() * 600,
      cost_usd: 0.0008 + Math.random() * 0.0004,
    },
    composite_fitness: g.fitness_composite,
    retrieval_trace: [
      { chunk_id: 'chunk_a91', score: 0.91, position: 0 },
      { chunk_id: 'chunk_b12', score: 0.84, position: 1 },
      { chunk_id: 'chunk_c44', score: 0.79, position: 2 },
    ],
  })),
  fitness: {
    relevance: 0.84,
    accuracy: 0.88,
    coverage: 0.72,
    latency_ms: 1120,
    cost_usd: 0.00091,
  },
  latency_ms: 1120,
};

export const mockEvents: EvolutionEvent[] = [
  {
    type: 'query.started',
    timestamp: new Date(Date.now() - 1000 * 4).toISOString(),
    data: { run_id: 'run_demo_001', query_text: 'How do I tune Atlas Vector Search?', n_genomes: 3 },
  },
  {
    type: 'evaluation.created',
    timestamp: new Date(Date.now() - 1000 * 3).toISOString(),
    data: { genome_id: 'g4_a', query_id: 'q42', composite_fitness: 0.78, generation: 4 },
  },
  {
    type: 'generation.evolved',
    timestamp: new Date(Date.now() - 1000 * 2).toISOString(),
    data: { generation: 4, best_fitness: 0.78, mean_fitness: 0.66, n_offspring: 4 },
  },
  {
    type: 'champion.promoted',
    timestamp: new Date(Date.now() - 1000 * 1).toISOString(),
    data: { champion_id: 'champ_001', original_genome_id: 'g3_a', peak_fitness: 0.74 },
  },
];
