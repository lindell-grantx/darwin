import type {
  Champion,
  FitnessCurveResponse,
  LineageResponse,
  PopulationResponse,
  QueryResponse,
} from '@contracts';

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

export function getFitnessCurve(): Promise<FitnessCurveResponse> {
  return get('/fitness-curve');
}

export function getPopulation(): Promise<PopulationResponse> {
  return get('/population');
}

export function getLineage(genomeId: string): Promise<LineageResponse> {
  return get(`/lineage/${encodeURIComponent(genomeId)}`);
}

export function getChampions(): Promise<Champion[]> {
  return get('/champions');
}

export function postQuery(text: string): Promise<QueryResponse> {
  return post('/query', { text });
}
