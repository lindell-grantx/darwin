import { Hono } from 'hono';
import { champions as championsCol } from '../db/client.ts';
import { toChampionRecord } from '../db/mappers.ts';

export const champions = new Hono();

champions.get('/', async (c) => {
  const docs = await championsCol().find().sort({ composite_fitness: -1 }).toArray();
  return c.json(docs.map(toChampionRecord));
});
