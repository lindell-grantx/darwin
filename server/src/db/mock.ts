import type {
  ChampionRecord,
  EvolutionEvent,
  FitnessCurveResponse,
  GenerationsResponse,
  GenomeSummary,
  LineageResponse,
  PopulationResponse,
  QueryResponse,
} from '../../../src/contracts.ts';

const genome = (id: string, generation: number, fitness: number): GenomeSummary => ({
  id,
  generation,
  status: 'alive',
  fitness: { composite: fitness, last_updated: new Date().toISOString() },
  retrieval_genes: {
    embedding_model: 'gemini_1536',
    chunk_size: 512,
    chunk_overlap: 0.1,
    query_transform: 'none',
    rerank: 'none',
    confidence_threshold: 0.5,
    source_routing: ['docs'],
  },
  coordination_genes: {
    protocol: 'solo',
    consultation_count: 0,
    disagreement_resolver: 'majority_vote',
    timeout_ms: 5000,
  },
  durability_genes: {
    memory_strategy: 'none',
    checkpoint_every_n_turns: 5,
    context_compression: 'none',
  },
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
  generation: 4,
  population_size: POP.length,
  genomes: POP,
};

export const mockGenerations: GenerationsResponse = {
  generations: mockFitnessCurve.series.map((p) => ({
    generation: p.generation,
    created_at: new Date(Date.now() - (4 - p.generation) * 60_000).toISOString(),
    population_size: POP.length,
    best_fitness: p.best,
    mean_fitness: p.mean,
    diversity_index: p.diversity,
    selection: 'tournament',
    crossover_rate: 1.0,
    mutation_rate: 0.1,
  })),
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
  const seen = new Set<string>();
  const nodes: LineageResponse['nodes'] = [];
  const queue: string[] = [genomeId];
  while (queue.length > 0) {
    const cur = queue.shift()!;
    if (seen.has(cur)) continue;
    seen.add(cur);
    const g = POP.find((p) => p.id === cur);
    if (!g) continue;
    const parentId = LINEAGE_PARENTS[cur];
    nodes.push({
      id: g.id,
      generation: g.generation,
      parent_ids: parentId ? [parentId] : [],
      fitness: g.fitness,
      retrieval_genes: g.retrieval_genes,
      is_champion: cur === 'g3_a',
    });
    if (parentId) queue.push(parentId);
  }
  return { genome_id: genomeId, nodes };
}

export const mockChampions: ChampionRecord[] = [
  {
    id: 'champ_001',
    original_genome_id: 'g3_a',
    peak_fitness: 0.74,
    generations_alive: 3,
    lineage: ['g0_a', 'g1_a', 'g2_a', 'g3_a'],
    retired_at: new Date(Date.now() - 1000 * 60 * 8).toISOString(),
    genome: POP.find((g) => g.id === 'g3_a')!,
  },
];

export function mockQueryResponse(queryText: string): QueryResponse {
  const winner = POP[POP.length - 1]!;
  return {
    run_id: `run_mock_${Date.now()}`,
    answer:
      'MongoDB Atlas Vector Search uses HNSW indexes by default. For 1M+ vectors at scale, tune `numCandidates` ≥ 10× `limit` and prefer cosine similarity for normalized embeddings.\n\n' +
      `Query: ${queryText}`,
    winning_genome: winner,
    fitness: {
      relevance: 0.84,
      accuracy: 0.88,
      latency_ms: 1120,
      cost_usd: 0.00091,
    },
    composite_fitness: winner.fitness.composite,
    retrieval_trace: [
      { chunk_id: 'chunk_a91', score: 0.91, position: 0 },
      { chunk_id: 'chunk_b12', score: 0.84, position: 1 },
      { chunk_id: 'chunk_c44', score: 0.79, position: 2 },
    ],
  };
}

export const mockInitialEvents: EvolutionEvent[] = [
  {
    event_type: 'generation.evolved',
    generation: 3,
    timestamp: new Date(Date.now() - 1000 * 4).toISOString(),
    data: { best_fitness: 0.71, mean_fitness: 0.6, n_offspring: 4 },
  },
  {
    event_type: 'generation.evolved',
    generation: 4,
    timestamp: new Date(Date.now() - 1000 * 2).toISOString(),
    data: { best_fitness: 0.78, mean_fitness: 0.66, n_offspring: 4 },
  },
  {
    event_type: 'champion.promoted',
    generation: 3,
    timestamp: new Date(Date.now() - 1000 * 1).toISOString(),
    data: { champion_id: 'champ_001', original_genome_id: 'g3_a', peak_fitness: 0.74 },
  },
];

export function nextMockEvent(): EvolutionEvent {
  return {
    event_type: 'genome.born',
    generation: 4,
    timestamp: new Date().toISOString(),
    data: {
      genome_id: `g_mock_${Math.floor(Math.random() * 99)}`,
      fitness: 0.6 + Math.random() * 0.3,
    },
  };
}

export async function withMock<T>(real: () => Promise<T | null>, mock: T): Promise<T> {
  try {
    const result = await real();
    return result ?? mock;
  } catch (err) {
    console.warn('[mock fallback]', err instanceof Error ? err.message : err);
    return mock;
  }
}
