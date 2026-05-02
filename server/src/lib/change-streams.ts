import type { ChangeStream } from 'mongodb';
import { champions, fitnessEvaluations, generations, genomes } from '../db/client.ts';
import { publish } from './event-bus.ts';

const streams: ChangeStream[] = [];

export function startChangeStreams(): void {
  watchFitness();
  watchGenomes();
  watchChampions();
  watchGenerations();
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
  const stream = fitnessEvaluations().watch(
    [{ $match: { operationType: 'insert' } }],
    { fullDocument: 'updateLookup' },
  );
  stream.on('change', (change) => {
    if (change.operationType !== 'insert' || !change.fullDocument) return;
    const doc = change.fullDocument;
    publish({
      event_type: 'query.completed',
      generation: doc.generation,
      timestamp: doc.timestamp.toISOString(),
      data: {
        run_id: doc.run_id,
        genome_id: doc.genome_id.toHexString(),
        query_id: doc.query_id.toHexString(),
        composite_fitness: doc.composite_fitness,
      },
    });
  });
  attachErrorLogger(stream, 'fitness_evaluations');
  streams.push(stream);
}

function watchGenomes(): void {
  const stream = genomes().watch(
    [{ $match: { operationType: { $in: ['insert', 'update'] } } }],
    { fullDocument: 'updateLookup' },
  );
  stream.on('change', (change) => {
    if (!('fullDocument' in change) || !change.fullDocument) return;
    const doc = change.fullDocument;

    if (change.operationType === 'insert') {
      publish({
        event_type: 'genome.born',
        generation: doc.generation,
        timestamp: doc.created_at.toISOString(),
        data: {
          genome_id: doc._id.toHexString(),
          parent_ids: doc.parent_ids.map((id) => id.toHexString()),
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
          genome_id: doc._id.toHexString(),
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
      generation: doc.genome.generation,
      timestamp: doc.promoted_at.toISOString(),
      data: {
        champion_id: doc._id.toHexString(),
        original_genome_id: doc.original_genome_id.toHexString(),
        peak_fitness: doc.peak_fitness,
      },
    });
  });
  attachErrorLogger(stream, 'champions');
  streams.push(stream);
}

function watchGenerations(): void {
  const stream = generations().watch([{ $match: { operationType: 'insert' } }]);
  stream.on('change', (change) => {
    if (change.operationType !== 'insert' || !change.fullDocument) return;
    const doc = change.fullDocument;
    publish({
      event_type: 'generation.evolved',
      generation: doc.generation,
      timestamp: doc.created_at.toISOString(),
      data: {
        best_fitness: doc.best_fitness,
        mean_fitness: doc.mean_fitness,
        diversity_index: doc.diversity_index,
        population_size: doc.population_size,
      },
    });
  });
  attachErrorLogger(stream, 'generations');
  streams.push(stream);
}
