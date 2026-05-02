import { serve } from '@hono/node-server';
import { app } from './app.ts';
import { connect, disconnect } from './db/client.ts';
import { env, requireSecret } from './env.ts';
import { startChangeStreams, stopChangeStreams } from './lib/change-streams.ts';

async function main() {
  const uri = requireSecret('MONGODB_URI');
  await connect(uri);
  console.log('mongodb connected');

  try {
    startChangeStreams();
    console.log('change streams started');
  } catch (err) {
    // Replica set required; non-fatal — endpoints still work, SSE just won't emit live events.
    console.warn('change streams could not start (need replica set):', err);
  }

  const server = serve({ fetch: app.fetch, port: env.PORT }, (info) => {
    console.log(`darwin server listening on http://localhost:${info.port}`);
  });

  for (const sig of ['SIGTERM', 'SIGINT']) {
    process.once(sig, async () => {
      server.close();
      await stopChangeStreams();
      await disconnect();
      process.exit(0);
    });
  }
}

main().catch((err) => {
  console.error('startup failed:', err);
  process.exit(1);
});
