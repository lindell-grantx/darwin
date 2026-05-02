import { Hono } from 'hono';
import { streamSSE } from 'hono/streaming';
import { mockInitialEvents, nextMockEvent } from '../db/mock.ts';

export const events = new Hono();

// GET /events — SSE stream of evolution events.
// TODO(stream-d): subscribe to a real event bus driven by Mongo change streams.
// For now: replay an initial batch of mock events, then emit a new one every 6s.
events.get('/', (c) =>
  streamSSE(c, async (stream) => {
    let id = 0;

    for (const ev of mockInitialEvents) {
      await stream.writeSSE({ id: String(id++), data: JSON.stringify(ev) });
    }

    while (!stream.aborted) {
      await stream.sleep(6000);
      if (stream.aborted) break;
      await stream.writeSSE({ id: String(id++), data: JSON.stringify(nextMockEvent()) });
    }
  }),
);
