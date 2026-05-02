import type { ChangeStream } from 'mongodb';
import { champions, evolutionEvents, fitnessEvaluations, genomes } from '../db/client.ts';
import { idToString, toIso } from '../db/mappers.ts';
import { publish } from './event-bus.ts';

const streams: ChangeStream[] = [];

export function startChangeStreams(): void {
  watchFitness();
  watchGenomes();
  watchChampions();
  // `generations` is a timeseries collection; Mongo can't run a $match-aggregation
  // change stream on it. The Python conductor mirrors every rollover into
  // `evolution_events`, which we watch below.
  watchEvolutionEvents();
}

export async function stopChangeStreams(): Promise<void> {
  await Promise.allSettled(streams.map((s) => s.close()));
  streams.length = 0;
}

function attachErrorLogger(stream: ChangeStream, label: string): void {
  stream.on('error', (err) => {
    // Most common cause: standalone MongoDB (change streams require a replica set).
    // Log once and keep the server running — SSE just won't emit real events.
    console.error(`[change-stream:${label}]`, err instanceof Error ? err.message : err);
  });
}

function watchFitness(): void {
  const stream = fitnessEvaluations().watch([{ $match: { operationType: 'insert' } }], {
    fullDocument: 'updateLookup',
  });
  stream.on('change', (change) => {
    if (change.operationType !== 'insert' || !change.fullDocument) return;
    const doc = change.fullDocument;
    publish({
      event_type: 'query.completed',
      generation: doc.generation,
      timestamp: new Date().toISOString(),
      data: {
        run_id: doc.run_id,
        genome_id: idToString(doc.genome_id),
        query_id: idToString(doc.query_id),
        composite_fitness: doc.composite_fitness,
      },
    });
  });
  attachErrorLogger(stream, 'fitness_evaluations');
  streams.push(stream);
}

function watchGenomes(): void {
  const stream = genomes().watch([{ $match: { operationType: { $in: ['insert', 'update'] } } }], {
    fullDocument: 'updateLookup',
  });
  stream.on('change', (change) => {
    if (!('fullDocument' in change) || !change.fullDocument) return;
    const doc = change.fullDocument;

    if (change.operationType === 'insert') {
      publish({
        event_type: 'genome.born',
        generation: doc.generation,
        timestamp: toIso(doc.created_at) ?? new Date().toISOString(),
        data: {
          genome_id: idToString(doc._id),
          parent_ids: doc.parent_ids.map(idToString),
          fitness: doc.fitness.composite,
        },
      });
      return;
    }

    if (change.operationType === 'update' && doc.status === 'retired') {
      const updated = change.updateDescription?.updatedFields ?? {};
      const becameRetired = 'status' in updated;
      if (!becameRetired) return;
      publish({
        event_type: 'genome.retired',
        generation: doc.generation,
        timestamp: new Date().toISOString(),
        data: {
          genome_id: idToString(doc._id),
          final_fitness: doc.fitness.composite,
        },
      });
    }
  });
  attachErrorLogger(stream, 'genomes');
  streams.push(stream);
}

function watchChampions(): void {
  const stream = champions().watch([{ $match: { operationType: 'insert' } }]);
  stream.on('change', (change) => {
    if (change.operationType !== 'insert' || !change.fullDocument) return;
    const doc = change.fullDocument;
    publish({
      event_type: 'champion.promoted',
      generation: doc.promoted_at_generation,
      timestamp: toIso(doc.created_at) ?? new Date().toISOString(),
      data: {
        champion_id: idToString(doc._id),
        genome_id: idToString(doc.genome_id),
        composite_fitness: doc.composite_fitness,
      },
    });
  });
  attachErrorLogger(stream, 'champions');
  streams.push(stream);
}

function watchEvolutionEvents(): void {
  const stream = evolutionEvents().watch([{ $match: { operationType: 'insert' } }]);
  stream.on('change', (change) => {
    if (change.operationType !== 'insert' || !change.fullDocument) return;
    const doc = change.fullDocument;
    if (doc.event_type !== 'generation.evolved') return;
    publish({
      event_type: 'generation.evolved',
      generation: doc.generation,
      timestamp: toIso(doc.created_at) ?? new Date().toISOString(),
      data: doc.payload,
    });
  });
  attachErrorLogger(stream, 'evolution_events');
  streams.push(stream);
}
