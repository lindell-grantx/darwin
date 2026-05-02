import { Hono } from 'hono';
import { streamSSE } from 'hono/streaming';
import type { EvolutionEvent } from '../../../src/contracts.ts';
import { champions, fitnessEvaluations } from '../db/client.ts';
import { idToString, toIso } from '../db/mappers.ts';
import { subscribe } from '../lib/event-bus.ts';

export const events = new Hono();

const HEARTBEAT_MS = 15_000;
const POLL_MS = 1_000;
const REPLAY_LIMIT = 20;

// GET /events — SSE stream of evolution events.
// On connect: replay a small history pulled directly from the DB so a freshly
// connected client has context. Then subscribe to the in-process event bus,
// which is fed by Mongo change streams (see lib/change-streams.ts).
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

    // Replay recent history from the DB so the UI isn't blank on reconnect.
    try {
      for (const ev of await loadInitialReplay()) writeEvent(ev);
    } catch (err) {
      console.warn('[events] initial replay failed:', err instanceof Error ? err.message : err);
    }

    const unsubscribe = subscribe(writeEvent);

    try {
      let elapsedSinceHeartbeat = 0;
      while (!stream.aborted) {
        await stream.sleep(POLL_MS);
        if (stream.aborted) break;

        elapsedSinceHeartbeat += POLL_MS;
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
      await writeChain;
    }
  }),
);

async function loadInitialReplay(): Promise<EvolutionEvent[]> {
  const replay: EvolutionEvent[] = [];

  const recentChampions = await champions()
    .find()
    .sort({ created_at: -1 })
    .limit(REPLAY_LIMIT)
    .toArray();

  for (const ch of recentChampions.reverse()) {
    replay.push({
      event_type: 'champion.promoted',
      generation: ch.promoted_at_generation,
      timestamp: toIso(ch.created_at) ?? new Date().toISOString(),
      data: {
        champion_id: idToString(ch._id),
        genome_id: idToString(ch.genome_id),
        composite_fitness: ch.composite_fitness,
      },
    });
  }

  const recentEvals = await fitnessEvaluations()
    .find()
    .sort({ generation: -1 })
    .limit(REPLAY_LIMIT)
    .toArray();

  for (const ev of recentEvals.reverse()) {
    replay.push({
      event_type: 'query.completed',
      generation: ev.generation,
      timestamp: new Date().toISOString(),
      data: {
        run_id: ev.run_id,
        genome_id: idToString(ev.genome_id),
        query_id: idToString(ev.query_id),
        composite_fitness: ev.composite_fitness,
      },
    });
  }

  return replay;
}
