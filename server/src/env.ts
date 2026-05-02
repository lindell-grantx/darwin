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
  MONGODB_URI: process.env.MONGODB_URI ?? '',
  VOYAGE_API_KEY: process.env.VOYAGE_API_KEY ?? '',
  ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY ?? '',
};
