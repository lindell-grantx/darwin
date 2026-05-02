import { useEffect, useRef, useState } from 'react';

import type { EvolutionEvent } from '@contracts';

import { getFitnessCurve, getPopulation } from './api';

const SSE_URL = `${(import.meta.env.VITE_API_URL as string | undefined) ?? ''}/events`;

const MAX_EVENTS = 50;

/**
 * Subscribes to /events as an SSE stream. If the connection drops or never
 * opens, falls back to polling /fitness-curve + /population every 2s and
 * synthesizing `generation.evolved` events from the deltas.
 */
export function useEvolutionEvents(): EvolutionEvent[] {
  const [events, setEvents] = useState<EvolutionEvent[]>([]);
  const lastBest = useRef<number | null>(null);

  useEffect(() => {
    let es: EventSource | null = null;
    let pollId: number | null = null;

    const startPolling = () => {
      if (pollId !== null) return;
      pollId = window.setInterval(async () => {
        try {
          const [curve, pop] = await Promise.all([getFitnessCurve(), getPopulation()]);
          const last = curve.series.at(-1);
          if (!last) return;
          if (lastBest.current !== null && last.best === lastBest.current) return;
          lastBest.current = last.best;
          setEvents((prev) => [
            ...prev.slice(-MAX_EVENTS + 1),
            {
              type: 'generation.evolved',
              timestamp: new Date().toISOString(),
              data: {
                generation: last.generation,
                best_fitness: last.best,
                mean_fitness: last.mean,
                n_offspring: pop.alive_count,
              },
            },
          ]);
        } catch {
          // swallow — next tick will retry
        }
      }, 2000);
    };

    try {
      es = new EventSource(SSE_URL);
      const fallbackTimer = window.setTimeout(() => {
        if (es && es.readyState !== EventSource.OPEN) startPolling();
      }, 5000);
      es.onmessage = (e) => {
        try {
          const ev = JSON.parse(e.data) as EvolutionEvent;
          setEvents((prev) => [...prev.slice(-MAX_EVENTS + 1), ev]);
        } catch {
          /* ignore malformed payload */
        }
      };
      es.onopen = () => window.clearTimeout(fallbackTimer);
      es.onerror = () => {
        es?.close();
        startPolling();
      };
    } catch {
      startPolling();
    }

    return () => {
      es?.close();
      if (pollId !== null) window.clearInterval(pollId);
    };
  }, []);

  return events;
}
