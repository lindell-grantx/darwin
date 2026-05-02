import { Hono } from 'hono';
import type { LineageNode, LineageResponse } from '../../../src/contracts.ts';
import { champions as championsCol, genomes } from '../db/client.ts';
import { idToString, toIso } from '../db/mappers.ts';
import type { GenomeDoc } from '../db/types.ts';

export const lineage = new Hono();

lineage.get('/:genomeId', async (c) => {
  const idStr = c.req.param('genomeId');
  const rootDoc = await genomes().findOne({ _id: idStr });
  if (!rootDoc) return c.json({ error: 'genome_not_found', id: idStr }, 404);

  // BFS up the ancestry tree, capped at 50 nodes.
  const collected = new Map<string, GenomeDoc>();
  collected.set(idToString(rootDoc._id), rootDoc);
  const queue: GenomeDoc[] = [rootDoc];

  while (queue.length > 0 && collected.size < 50) {
    const doc = queue.shift()!;
    if (doc.parent_ids.length === 0) continue;
    const parents = await genomes()
      .find({ _id: { $in: doc.parent_ids } })
      .toArray();
    for (const parent of parents) {
      const pid = idToString(parent._id);
      if (!collected.has(pid)) {
        collected.set(pid, parent);
        queue.push(parent);
      }
    }
  }

  const championIds = new Set(
    (
      await championsCol()
        .find({}, { projection: { genome_id: 1 } })
        .toArray()
    ).map((ch) => idToString(ch.genome_id)),
  );

  const nodes: LineageNode[] = [...collected.values()].map((doc) => ({
    id: idToString(doc._id),
    generation: doc.generation,
    parent_ids: doc.parent_ids.map(idToString),
    fitness: {
      composite: doc.fitness.composite,
      n_evaluations: doc.fitness.n_evaluations,
      last_updated: toIso(doc.fitness.last_updated),
    },
    retrieval_genes: doc.retrieval_genes,
    is_champion: championIds.has(idToString(doc._id)),
  }));

  const response: LineageResponse = { genome_id: idStr, nodes };
  return c.json(response);
});
