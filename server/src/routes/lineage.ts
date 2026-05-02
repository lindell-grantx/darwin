import { Hono } from 'hono';

export const lineage = new Hono();

// GET /lineage/:genomeId — ancestor DAG via parent_ids walk
lineage.get('/:genomeId', async (c) => {
  const genomeId = c.req.param('genomeId');
  // TODO(stream-b): recursive parent_ids walk, return DAG nodes + edges
  return c.json({ genome_id: genomeId, ancestors: [] });
});
