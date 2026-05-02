import { serve } from '@hono/node-server';
import { app } from './app.ts';
import { connect, disconnect } from './db/client.ts';
import { env } from './env.ts';
import { startChangeStreams, stopChangeStreams } from './lib/change-streams.ts';

async function main() {
  let mongoConnected = false;
  if (env.MONGODB_URI) {
    try {
      await connect(env.MONGODB_URI);
      console.log('mongodb connected');
      mongoConnected = true;
    } catch (err) {
      console.warn('mongodb connection failed, continuing in mock-only mode:', err);
    }
  } else {
    console.warn('MONGODB_URI not set, running in mock-only mode');
  }

  if (mongoConnected) {
    try {
      startChangeStreams();
      console.log('change streams started');
    } catch (err) {
      console.warn('change streams could not start (need replica set):', err);
    }
  }

  const server = serve({ fetch: app.fetch, port: env.PORT }, (info) => {
    console.log(`darwin server listening on http://localhost:${info.port}`);
  });

  for (const sig of ['SIGTERM', 'SIGINT']) {
    process.once(sig, async () => {
      server.close();
      if (mongoConnected) await stopChangeStreams();
      await disconnect();
      process.exit(0);
    });
  }
}

main().catch((err) => {
  console.error('startup failed:', err);
  process.exit(1);
});
