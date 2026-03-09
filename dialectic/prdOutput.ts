// Minimal TypeScript utility to read PRD_OUTPUT_FORMAT from environment
// Behavior:
// - Accepts 'md', 'json', 'both' (any case).
// - Returns normalized lowercase string.
// - Falls back to 'json' if absent or invalid.

export type PrdOutputFormat = 'md' | 'json' | 'both';
const ALLOWED: PrdOutputFormat[] = ['md', 'json', 'both'];
const FALLBACK: PrdOutputFormat = 'json';

export function getPrdOutputFormat(env: NodeJS.ProcessEnv = process.env): PrdOutputFormat {
  const raw = env['PRD_OUTPUT_FORMAT'];
  if (!raw) return FALLBACK;
  const v = String(raw).trim().toLowerCase();
  if (ALLOWED.includes(v as PrdOutputFormat)) return v as PrdOutputFormat;
  return FALLBACK;
}

// quick manual run when executed directly with ts-node
if (require.main === module) {
  // eslint-disable-next-line no-console
  console.log('PRD_OUTPUT_FORMAT ->', getPrdOutputFormat());
}
