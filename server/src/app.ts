import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { champions } from './routes/champions.ts';
import { events } from './routes/events.ts';
import { fitnessCurve } from './routes/fitness-curve.ts';
import { generations } from './routes/generations.ts';
import { health } from './routes/health.ts';
import { lineage } from './routes/lineage.ts';
import { population } from './routes/population.ts';
import { query } from './routes/query.ts';

export const app = new Hono();

app.use('*', logger());
app.use('*', cors());

app.route('/health', health);
app.route('/query', query);
app.route('/population', population);
app.route('/generations', generations);
app.route('/fitness-curve', fitnessCurve);
app.route('/lineage', lineage);
app.route('/champions', champions);
app.route('/events', events);

app.notFound((c) => c.json({ error: 'not_found', path: c.req.path }, 404));

app.onError((err, c) => {
  console.error(err);
  return c.json({ error: 'internal_error', message: err.message }, 500);
});
