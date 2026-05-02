import { Hono } from 'hono';
import { ObjectId } from 'mongodb';
import type { LineageResponse } from '../../../src/contracts.ts';
import { genomes } from '../db/client.ts';
import { computeGeneDiff, toGenomeSummary } from '../db/mappers.ts';

export const lineage = new Hono();

lineage.get('/:genomeId', async (c) => {
  const idStr = c.req.param('genomeId');

  let oid: ObjectId;
  try {
    oid = new ObjectId(idStr);
  } catch {
    return c.json({ error: 'invalid_genome_id' }, 400);
  }

  const rootDoc = await genomes().findOne({ _id: oid });
  if (!rootDoc) return c.json({ error: 'genome_not_found' }, 404);

  const ancestors: LineageResponse['ancestors'] = [];
  const queue: Array<{ doc: typeof rootDoc; depth: number }> = [{ doc: rootDoc, depth: 0 }];
  const seen = new Set<string>([idStr]);

  while (queue.length > 0) {
    const { doc, depth } = queue.shift()!;
    if (depth >= 10 || doc.parent_ids.length === 0) continue;

    const parents = await genomes()
      .find({ _id: { $in: doc.parent_ids } })
      .toArray();

    for (const parent of parents) {
      const parentId = parent._id.toHexString();
      if (seen.has(parentId)) continue;
      seen.add(parentId);
      ancestors.push({
        genome: toGenomeSummary(parent),
        gene_diff: computeGeneDiff(parent, doc),
        depth: depth + 1,
      });
      queue.push({ doc: parent, depth: depth + 1 });
    }
  }

  return c.json({
    genome: toGenomeSummary(rootDoc),
    ancestors,
  } satisfies LineageResponse);
});
