import { Hono } from 'hono';
import { ObjectId } from 'mongodb';
import type { LineageNode, LineageResponse } from '../../../src/contracts.ts';
import { champions as championsCol, genomes } from '../db/client.ts';
import { mockLineage, withMock } from '../db/mock.ts';

export const lineage = new Hono();

lineage.get('/:genomeId', async (c) => {
  const idStr = c.req.param('genomeId');

  const data = await withMock<LineageResponse>(async () => {
    let oid: ObjectId;
    try {
      oid = new ObjectId(idStr);
    } catch {
      return null;
    }

    const rootDoc = await genomes().findOne({ _id: oid });
    if (!rootDoc) return null;

    // BFS up the ancestry tree, capped at 50 nodes.
    type GenomeDoc = typeof rootDoc;
    const collected = new Map<string, GenomeDoc>();
    collected.set(idStr, rootDoc);
    const queue: GenomeDoc[] = [rootDoc];

    while (queue.length > 0 && collected.size < 50) {
      const doc = queue.shift()!;
      if (doc.parent_ids.length === 0) continue;
      const parents = await genomes()
        .find({ _id: { $in: doc.parent_ids } })
        .toArray();
      for (const parent of parents) {
        const pid = parent._id.toHexString();
        if (!collected.has(pid)) {
          collected.set(pid, parent);
          queue.push(parent);
        }
      }
    }

    const championIds = new Set(
      (await championsCol()
        .find({}, { projection: { original_genome_id: 1 } })
        .toArray()).map((ch) => ch.original_genome_id.toHexString()),
    );

    const nodes: LineageNode[] = [...collected.values()].map((doc) => ({
      id: doc._id.toHexString(),
      generation: doc.generation,
      parent_ids: doc.parent_ids.map((id) => id.toHexString()),
      fitness: {
        composite: doc.fitness.composite,
        last_updated: doc.fitness.last_updated.toISOString(),
      },
      retrieval_genes: doc.retrieval_genes,
      is_champion: championIds.has(doc._id.toHexString()),
    }));

    return { genome_id: idStr, nodes };
  }, mockLineage(idStr));

  return c.json(data);
});
