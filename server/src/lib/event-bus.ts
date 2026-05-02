import type { EvolutionEvent } from '../../../src/contracts.ts';

type Listener = (event: EvolutionEvent) => void;

const listeners = new Set<Listener>();

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function publish(event: EvolutionEvent): void {
  for (const listener of listeners) {
    try {
      listener(event);
    } catch (err) {
      console.error('[event-bus] listener threw:', err);
    }
  }
}
