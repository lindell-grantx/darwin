import type {
  ChampionRecord,
  FitnessCurveResponse,
  GenomeSummary,
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

export function getFitnessCurve(): Promise<FitnessCurveResponse> {
  return get('/fitness-curve');
}

export function getPopulation(): Promise<PopulationResponse> {
  return get('/population');
}

export function getLineage(genomeId: string): Promise<LineageResponse> {
  return get(`/lineage/${encodeURIComponent(genomeId)}`);
}

export function getChampions(): Promise<ChampionRecord[]> {
  return get('/champions');
}

// ─── /query SSE consumer ──────────────────────────────────────────────────────

export type QueryStage =
  | 'starting'
  | 'retrieving'
  | 'generating'
  | 'judging'
  | 'persisting';

export interface QueryChunkEvent {
  chunk_id: string;
  score: number;
  position: number;
  text_preview?: string;
}

export interface QueryStreamHandlers {
  onProgress?: (stage: QueryStage | string) => void;
  onGenome?: (genome: GenomeSummary) => void;
  onChunk?: (chunk: QueryChunkEvent) => void;
  onToken?: (delta: string) => void;
  onDone?: (final: QueryResponse) => void;
  onError?: (message: string) => void;
}

// Streams `/query` and dispatches per-event callbacks. Resolves on the `done`
// event; rejects on transport errors or `error` events from the server.
export async function streamQuery(
  text: string,
  handlers: QueryStreamHandlers = {},
  signal?: AbortSignal,
): Promise<QueryResponse> {
  const t0 = performance.now();
  console.log('[query] POST start', { text_len: text.length, api: API || '(same-origin)' });

  const res = await fetch(`${API}/query`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      accept: 'text/event-stream',
    },
    body: JSON.stringify({ text }),
    signal,
  });

  console.log('[query] response headers', {
    status: res.status,
    content_type: res.headers.get('content-type'),
    cache_control: res.headers.get('cache-control'),
    elapsed_ms: Math.round(performance.now() - t0),
  });

  if (!res.ok || !res.body) {
    const detail = await res.text().catch(() => '');
    console.error('[query] non-streaming error response', { status: res.status, detail });
    throw new Error(`/query → ${res.status}${detail ? `: ${detail.slice(0, 300)}` : ''}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let final: QueryResponse | null = null;
  let lastError: string | null = null;
  let chunkCount = 0;
  let bytesIn = 0;
  let eventCount = 0;
  const eventCounts: Record<string, number> = {};

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        console.log('[query] stream ended', {
          chunks_read: chunkCount,
          bytes_in: bytesIn,
          events: eventCount,
          event_counts: eventCounts,
          elapsed_ms: Math.round(performance.now() - t0),
        });
        break;
      }
      chunkCount += 1;
      bytesIn += value.byteLength;
      buffer += decoder.decode(value, { stream: true });
      console.log('[query] chunk', {
        n: chunkCount,
        bytes: value.byteLength,
        buf_len: buffer.length,
        t_ms: Math.round(performance.now() - t0),
      });

      while (true) {
        const match = buffer.match(/\r?\n\r?\n/);
        if (!match || match.index === undefined) break;
        const rawEvent = buffer.slice(0, match.index);
        buffer = buffer.slice(match.index + match[0].length);

        let eventName = 'message';
        const dataLines: string[] = [];
        for (const line of rawEvent.split(/\r?\n/)) {
          if (line.startsWith(':')) continue;
          if (line.startsWith('event:')) eventName = line.slice(6).replace(/^ /, '');
          else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''));
        }
        if (dataLines.length === 0) continue;
        const payload = dataLines.join('\n');
        eventCount += 1;
        eventCounts[eventName] = (eventCounts[eventName] ?? 0) + 1;

        if (eventName !== 'token') {
          console.log('[query] event', {
            n: eventCount,
            event: eventName,
            data_len: payload.length,
            t_ms: Math.round(performance.now() - t0),
          });
        }

        try {
          switch (eventName) {
            case 'progress': {
              const { stage } = JSON.parse(payload) as { stage: string };
              console.log('[query] → progress', { stage });
              handlers.onProgress?.(stage);
              break;
            }
            case 'genome': {
              const g = JSON.parse(payload) as GenomeSummary;
              console.log('[query] → genome', { id: g.id, generation: g.generation });
              handlers.onGenome?.(g);
              break;
            }
            case 'chunk': {
              const ch = JSON.parse(payload) as QueryChunkEvent;
              handlers.onChunk?.(ch);
              break;
            }
            case 'token': {
              const { delta } = JSON.parse(payload) as { delta: string };
              handlers.onToken?.(delta);
              break;
            }
            case 'done': {
              const f = JSON.parse(payload) as QueryResponse;
              console.log('[query] → done', {
                run_id: f.run_id,
                composite_fitness: f.composite_fitness,
                trace_len: f.retrieval_trace?.length,
              });
              final = f;
              handlers.onDone?.(f);
              break;
            }
            case 'error': {
              const { message } = JSON.parse(payload) as { message: string };
              console.error('[query] → error', { message });
              lastError = message;
              handlers.onError?.(message);
              break;
            }
            default:
              console.log('[query] → unknown event', { event: eventName });
              break;
          }
        } catch (err) {
          console.warn('[query] payload parse failed', {
            event: eventName,
            error: String(err),
            head: payload.slice(0, 200),
          });
        }
      }
    }
  } catch (err) {
    console.error('[query] reader error', err);
    throw err;
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // already released
    }
  }

  if (final) return final;
  throw new Error(lastError ?? 'query_stream_ended_without_done');
}

// Convenience wrapper for callers that don't care about progressive events.
export function postQuery(text: string): Promise<QueryResponse> {
  return streamQuery(text);
}
