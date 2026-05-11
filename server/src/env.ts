import { loadEnvFile } from 'node:process';

// Load .env from cwd (server/) using Node 24's native API.
// PM2 injects PORT/NODE_ENV via its env block — those win, since
// loadEnvFile does not override variables already set in process.env.
try {
  loadEnvFile();
} catch (err: unknown) {
  // ENOENT means no .env file — fine in prod/CI where env comes from the OS.
  if (err instanceof Error && 'code' in err && err.code !== 'ENOENT') {
    throw err;
  }
}

function readPort(): number {
  const raw = process.env.PORT ?? '3300';
  const n = Number(raw);
  if (!Number.isInteger(n) || n <= 0) {
    throw new Error(`Invalid PORT: ${raw}`);
  }
  return n;
}

export const env = {
  PORT: readPort(),
  NODE_ENV: process.env.NODE_ENV ?? 'development',

  MONGODB_URI: process.env.MONGODB_URI ?? '',

  VOYAGE_API_KEY: process.env.VOYAGE_API_KEY ?? '',

  ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY ?? '',
  ANTHROPIC_MODEL_JUDGE: process.env.ANTHROPIC_MODEL_JUDGE ?? 'claude-haiku-4-5-20251001',
  ANTHROPIC_MODEL_GENERATOR: process.env.ANTHROPIC_MODEL_GENERATOR ?? 'claude-sonnet-4-6',

  PYTHON_SERVICE_URL: process.env.PYTHON_SERVICE_URL ?? 'http://localhost:8080',

  LOG_LEVEL: process.env.LOG_LEVEL ?? 'info',
};

// Lazily assert a secret is present. Use inside route handlers / services that
// need it, so the server still boots without it for endpoints that don't.
export function requireSecret(
  name: 'MONGODB_URI' | 'VOYAGE_API_KEY' | 'ANTHROPIC_API_KEY',
): string {
  const v = env[name];
  if (!v) throw new Error(`Missing required env var: ${name}`);
  return v;
}
