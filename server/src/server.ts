import { serve } from '@hono/node-server';
import { app } from './app.ts';
import { connect, disconnect } from './db/client.ts';
import { env } from './env.ts';

async function main() {
  if (env.MONGODB_URI) {
    try {
      await connect(env.MONGODB_URI);
      console.log('mongodb connected');
    } catch (err) {
      console.warn('mongodb connection failed, continuing in mock-only mode:', err);
    }
  } else {
    console.warn('MONGODB_URI not set, running in mock-only mode');
  }

  const server = serve({ fetch: app.fetch, port: env.PORT }, (info) => {
    console.log(`darwin server listening on http://localhost:${info.port}`);
  });

  for (const sig of ['SIGTERM', 'SIGINT']) {
    process.once(sig, async () => {
      server.close();
      await disconnect();
      process.exit(0);
    });
  }
}

main().catch((err) => {
  console.error('startup failed:', err);
  process.exit(1);
});
