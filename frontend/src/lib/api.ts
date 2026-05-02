import type {
  Champion,
  FitnessCurveResponse,
  LineageResponse,
  PopulationResponse,
  QueryResponse,
} from '@contracts';

import {
  mockChampions,
  mockFitnessCurve,
  mockLineage,
  mockPopulation,
  mockQueryResponse,
} from './mock';

// Toggle to develop offline against fixtures.
const USE_MOCKS = (import.meta.env.VITE_USE_MOCKS ?? 'true') === 'true';

const API = (import.meta.env.VITE_API_URL as string | undefined) ?? '';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { headers: { accept: 'application/json' } });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return (await res.json()) as T;
}

async function post<T, B>(path: string, body: B): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return (await res.json()) as T;
}

export async function getFitnessCurve(): Promise<FitnessCurveResponse> {
  if (USE_MOCKS) return mockFitnessCurve;
  return get('/api/fitness-curve');
}

export async function getPopulation(): Promise<PopulationResponse> {
  if (USE_MOCKS) return mockPopulation;
  return get('/api/population');
}

export async function getLineage(genomeId: string): Promise<LineageResponse> {
  if (USE_MOCKS) return mockLineage(genomeId);
  return get(`/api/lineage/${encodeURIComponent(genomeId)}`);
}

export async function getChampions(): Promise<Champion[]> {
  if (USE_MOCKS) return mockChampions;
  return get('/api/champions');
}

export async function postQuery(text: string): Promise<QueryResponse> {
  if (USE_MOCKS) {
    await new Promise((r) => setTimeout(r, 700));
    return { ...mockQueryResponse, answer: `[mock] ${mockQueryResponse.answer}\n\nQuery: ${text}` };
  }
  return post('/api/query', { text });
}
