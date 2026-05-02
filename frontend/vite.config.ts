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
    // No proxy: the client talks to the API directly via VITE_API_URL.
    // Server handles CORS (see server/src/app.ts).
  },
});
