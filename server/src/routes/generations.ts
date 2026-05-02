import { Hono } from 'hono';
import type { GenerationsResponse } from '../../../src/contracts.ts';
import { generations as generationsCol } from '../db/client.ts';
import { toGenerationRecord } from '../db/mappers.ts';

export const generations = new Hono();

generations.get('/', async (c) => {
  const docs = await generationsCol().find().sort({ generation: 1 }).toArray();
  const response: GenerationsResponse = {
    generations: docs.map(toGenerationRecord),
  };
  return c.json(response);
});
