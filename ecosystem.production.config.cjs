// PM2 ecosystem config — PRODUCTION (server only)
//
// Frontend is a STATIC BUILD served by nginx — not managed by PM2.
// Workflow:
//   1. `npm run build` → produces frontend/dist (Vite bakes VITE_API_URL into the bundle)
//   2. nginx points its document root at .../darwin/frontend/dist
//   3. `npm start` boots the Hono server only
//
// `interpreter: 'node'` is pinned so PM2 cannot pick `bun` even when bun is in PATH.

module.exports = {
  apps: [
    {
      name: 'server',
      cwd: './server',
      script: 'src/server.ts',
      interpreter: 'node',
      env: {
        NODE_ENV: 'production',
        PORT: 3300,
      },
      max_restarts: 10,
      restart_delay: 1000,
    },
  ],
};
