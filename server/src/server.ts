import { serve } from '@hono/node-server';
import { app } from './app.ts';
import { connect, disconnect } from './db/client.ts';
import { env } from './env.ts';

async function main() {
  await connect(env.MONGODB_URI);
  console.log('mongodb connected');

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
