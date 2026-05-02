import { Hono } from 'hono';
import { streamSSE } from 'hono/streaming';

export const events = new Hono();

// GET /events — SSE stream of evolution events (generation.evolved, fitness.updated, ...)
events.get('/', (c) =>
  streamSSE(c, async (stream) => {
    // TODO(stream-d): subscribe to a real event bus driven by Mongo change streams.
    // For now, emit a heartbeat so clients can verify the channel is alive.
    let id = 0;
    while (!stream.aborted) {
      await stream.writeSSE({
        id: String(id++),
        event: 'heartbeat',
        data: JSON.stringify({ ts: new Date().toISOString() }),
      });
      await stream.sleep(15000);
    }
  }),
);
