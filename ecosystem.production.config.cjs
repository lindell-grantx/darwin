// PM2 ecosystem config — PRODUCTION (no watchers, built artifacts)
//
// Pre-req: `npm run build` must have produced frontend/dist before starting.
//
// Usage from repo root:
//   npm run build        → builds frontend (vite build → dist/)
//   npm start            → server + frontend preview, NODE_ENV=production
//   npm run start:full   → build + start, in one shot
//   npm run stop:prod    → kill all production apps
//
// Same `interpreter: 'node'` pinning as dev — bun can't sneak in.

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
    {
      name: 'frontend',
      cwd: './frontend',
      script: './node_modules/.bin/vite',
      interpreter: 'node',
      args: 'preview --host --port 5173',
      env: {
        NODE_ENV: 'production',
        VITE_API_URL: 'http://localhost:3300',
      },
      max_restarts: 10,
      restart_delay: 1000,
    },
  ],
};
