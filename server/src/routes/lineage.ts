import { Hono } from 'hono';
import { ObjectId } from 'mongodb';
import type { LineageNode, LineageResponse } from '../../../src/contracts.ts';
import { champions as championsCol, genomes } from '../db/client.ts';
import { idToString } from '../db/mappers.ts';
import { mockLineage, withMock } from '../db/mock.ts';

export const lineage = new Hono();

// Accept either a 24-char ObjectId hex or a plain string id (e.g. "g0_a").
function toIdQuery(idStr: string): ObjectId | string {
  try {
    return new ObjectId(idStr);
  } catch {
    return idStr;
  }
}

lineage.get('/:genomeId', async (c) => {
  const idStr = c.req.param('genomeId');

  const data = await withMock<LineageResponse>(async () => {
    const rootDoc = await genomes().findOne({ _id: toIdQuery(idStr) as never });
    if (!rootDoc) return null;

    // BFS up the ancestry tree, capped at 50 nodes.
    type GenomeDoc = typeof rootDoc;
    const collected = new Map<string, GenomeDoc>();
    collected.set(idToString(rootDoc._id), rootDoc);
    const queue: GenomeDoc[] = [rootDoc];

    while (queue.length > 0 && collected.size < 50) {
      const doc = queue.shift()!;
      if (doc.parent_ids.length === 0) continue;
      const parents = await genomes()
        .find({ _id: { $in: doc.parent_ids } as never })
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
          .find({}, { projection: { original_genome_id: 1 } })
          .toArray()
      ).map((ch) => idToString(ch.original_genome_id)),
    );

    const nodes: LineageNode[] = [...collected.values()].map((doc) => ({
      id: idToString(doc._id),
      generation: doc.generation,
      parent_ids: doc.parent_ids.map(idToString),
      fitness: {
        composite: doc.fitness.composite,
        last_updated: doc.fitness.last_updated.toISOString(),
      },
      retrieval_genes: doc.retrieval_genes,
      is_champion: championIds.has(idToString(doc._id)),
    }));

    return { genome_id: idStr, nodes };
  }, mockLineage(idStr));

  return c.json(data);
});
