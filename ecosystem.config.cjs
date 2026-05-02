// PM2 ecosystem config — DEV (live reload, watchers)
//
// Usage from repo root:
//   npm run dev          → server + frontend (foreground, Ctrl+C kills both)
//   npm run dev:server   → server only
//   npm run dev:frontend → frontend only
//   npm run logs         → tail aggregated logs
//   npm run stop         → kill all pm2-managed apps
//
// Both apps are pinned to `interpreter: 'node'` so PM2 can't pick `bun` even
// when bun is in PATH. The frontend calls Vite's bin directly to bypass any
// `npm` shell wrapper that might re-resolve to bun.

module.exports = {
  apps: [
    {
      name: 'server',
      cwd: './server',
      script: 'src/server.ts',
      interpreter: 'node',
      node_args: '--watch',
      env: {
        NODE_ENV: 'development',
        PORT: 3300,
      },
      max_restarts: 10,
      restart_delay: 500,
    },
    {
      name: 'frontend',
      cwd: './frontend',
      script: './node_modules/.bin/vite',
      interpreter: 'node',
      env: {
        NODE_ENV: 'development',
        // Vite reads port from vite.config.ts (5173, Vite default).
        // VITE_API_URL points the client at the Hono server on 3300.
        VITE_API_URL: 'http://localhost:3300',
      },
      max_restarts: 10,
      restart_delay: 500,
    },
  ],
};
