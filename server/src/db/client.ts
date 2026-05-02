import { type Collection, type Db, type Document, MongoClient } from 'mongodb';
import type {
  ChampionDoc,
  ChunkDoc,
  FitnessEvaluationDoc,
  GenerationDoc,
  GenomeDoc,
  QueryDoc,
} from './types.ts';

let client: MongoClient | null = null;
let db: Db | null = null;

const DB_NAME = 'darwin';

export async function connect(uri: string): Promise<void> {
  if (client) return;
  client = new MongoClient(uri, {
    serverSelectionTimeoutMS: 5000,
    connectTimeoutMS: 10000,
  });
  await client.connect();
  db = client.db(DB_NAME);
}

export async function disconnect(): Promise<void> {
  if (!client) return;
  await client.close();
  client = null;
  db = null;
}

export function ping(): Promise<Document> {
  return getDb().command({ ping: 1 });
}

export function getDb(): Db {
  if (!db) throw new Error('MongoDB not connected — call connect() first');
  return db;
}

// Typed collection accessors — one function per collection.

export function genomes(): Collection<GenomeDoc> {
  return getDb().collection<GenomeDoc>('genomes');
}

export function generations(): Collection<GenerationDoc> {
  return getDb().collection<GenerationDoc>('generations');
}

export function queries(): Collection<QueryDoc> {
  return getDb().collection<QueryDoc>('queries');
}

export function fitnessEvaluations(): Collection<FitnessEvaluationDoc> {
  return getDb().collection<FitnessEvaluationDoc>('fitness_evaluations');
}

export function chunks(): Collection<ChunkDoc> {
  return getDb().collection<ChunkDoc>('chunks');
}

export function champions(): Collection<ChampionDoc> {
  return getDb().collection<ChampionDoc>('champions');
}
