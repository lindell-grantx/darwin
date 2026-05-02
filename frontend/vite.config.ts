import path from 'node:path';
import { fileURLToPath } from 'node:url';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@contracts': path.resolve(__dirname, '../src/contracts.ts'),
    },
  },
  server: {
    port: 5173,
    fs: {
      // Allow importing src/contracts.ts from the parent directory.
      allow: [path.resolve(__dirname, '..')],
    },
    proxy: {
      // Backend (Hono) runs on PORT=3001 by default.
      '/api': { target: 'http://localhost:3001', changeOrigin: true },
      '/events': { target: 'http://localhost:3001', changeOrigin: true, ws: true },
    },
  },
});
