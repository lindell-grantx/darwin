import { Hono } from 'hono';
import { streamSSE } from 'hono/streaming';
import type { EvolutionEvent } from '../../../src/contracts.ts';
import { mockInitialEvents, nextMockEvent } from '../db/mock.ts';
import { subscribe } from '../lib/event-bus.ts';

export const events = new Hono();

const HEARTBEAT_MS = 15_000;
const MOCK_EMIT_MS = 6_000;

// GET /events — SSE stream of evolution events.
// Subscribes to the in-process event bus, which is fed by Mongo change streams
// (see lib/change-streams.ts). When change streams are unavailable (no replica
// set, no Mongo), falls back to emitting mock events on a timer so the UI has
// something to render during local development.
events.get('/', (c) =>
  streamSSE(c, async (stream) => {
    let id = 0;
    let writeChain: Promise<void> = Promise.resolve();

    const enqueue = (payload: { id?: string; event?: string; data: string }) => {
      writeChain = writeChain.then(async () => {
        if (stream.aborted) return;
        try {
          await stream.writeSSE(payload);
        } catch {
          // client disconnected mid-write
        }
      });
    };

    const writeEvent = (ev: EvolutionEvent) =>
      enqueue({ id: String(id++), data: JSON.stringify(ev) });

    // Replay a small history so a freshly-connected client has context.
    for (const ev of mockInitialEvents) writeEvent(ev);

    const unsubscribe = subscribe(writeEvent);
    let receivedReal = false;
    const trackReal = subscribe(() => {
      receivedReal = true;
    });

    try {
      let elapsedSinceHeartbeat = 0;
      while (!stream.aborted) {
        await stream.sleep(MOCK_EMIT_MS);
        if (stream.aborted) break;

        if (!receivedReal) writeEvent(nextMockEvent());

        elapsedSinceHeartbeat += MOCK_EMIT_MS;
        if (elapsedSinceHeartbeat >= HEARTBEAT_MS) {
          enqueue({
            event: 'heartbeat',
            data: JSON.stringify({ ts: new Date().toISOString() }),
          });
          elapsedSinceHeartbeat = 0;
        }
      }
    } finally {
      unsubscribe();
      trackReal();
      await writeChain;
    }
  }),
);
