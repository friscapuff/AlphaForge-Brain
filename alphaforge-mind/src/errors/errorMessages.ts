// Centralized UI-facing error taxonomy mapping (T094)
// Maps backend `detail` strings (or future explicit codes) to stable, user-friendly messages.

export interface ErrorDescriptor {
  code: string;               // Stable internal code (UPPER_SNAKE)
  title: string;              // Short label for UI surfaces / logs
  userMessage: string;        // Human-friendly explanation
  severity: 'info' | 'warn' | 'error';
  action?: string;            // Optional recommended user action
  http?: number;              // Typical HTTP status
}

// Raw backend detail strings observed (sampled) become keys here; if backend later adds structured codes
// we can pivot to keyed mapping. For now we treat detail text as a quasi-code.
// NOTE: Keep list alphabetized by code for diff stability.
export const ERROR_MAP: Record<string, ErrorDescriptor> = {
  'single symbol only (no comma separated list)': {
    code: 'SINGLE_SYMBOL_ONLY',
    title: 'Single Symbol',
    userMessage: 'Only one symbol can be backtested at a time. Remove additional tickers.',
    severity: 'error', http: 400,
  },
  'invalid symbol format': {
    code: 'INVALID_SYMBOL',
    title: 'Symbol Format',
    userMessage: 'The symbol contains unsupported characters. Use letters, numbers, dash or underscore only.',
    severity: 'error', http: 400,
  },
  'invalid configuration:': {
    code: 'INVALID_CONFIG_PREFIX',
    title: 'Configuration Error',
    userMessage: 'One or more configuration fields are invalid. Review date range, strategy, and risk parameters.',
    severity: 'error', http: 400,
  },
  'run not found': {
    code: 'RUN_NOT_FOUND',
    title: 'Run Missing',
    userMessage: 'The requested backtest run could not be located (it may have expired or never existed).',
    severity: 'error', http: 404,
  },
  'registry not initialized': {
    code: 'REGISTRY_UNAVAILABLE',
    title: 'Service Warming Up',
    userMessage: 'The run registry is not yet initialized. Retry shortly.',
    severity: 'warn', http: 500,
  },
  'registry unavailable': {
    code: 'REGISTRY_UNAVAILABLE_ALT',
    title: 'Service Unavailable',
    userMessage: 'Internal registry access failed. Please retry or contact support if persistent.',
    severity: 'error', http: 500,
  },
  'rate limit exceeded': {
    code: 'RATE_LIMIT',
    title: 'Too Many Requests',
    userMessage: 'You are performing Monte Carlo requests too quickly. Pause briefly and try again.',
    severity: 'warn', http: 429,
  },
  'limit must be positive': {
    code: 'INVALID_LIMIT',
    title: 'Invalid Limit',
    userMessage: 'List request limit must be a positive integer.',
    severity: 'error', http: 400,
  },
  'artifact not found': {
    code: 'ARTIFACT_NOT_FOUND',
    title: 'Artifact Missing',
    userMessage: 'Requested artifact does not exist for this run.',
    severity: 'error', http: 404,
  },
  'artifact unreadable': {
    code: 'ARTIFACT_UNREADABLE',
    title: 'Artifact Unreadable',
    userMessage: 'Stored artifact could not be read. It may be corrupted or incompatible.',
    severity: 'error', http: 500,
  },
  'to must be >= from': {
    code: 'RANGE_INVALID',
    title: 'Date Range',
    userMessage: 'The end date must not be earlier than the start date.',
    severity: 'error', http: 400,
  },
  'invalid interval': {
    code: 'INTERVAL_INVALID',
    title: 'Interval Unsupported',
    userMessage: 'The requested interval is not supported.',
    severity: 'error', http: 400,
  },
};

export const FALLBACK_ERROR: ErrorDescriptor = {
  code: 'UNKNOWN_ERROR',
  title: 'Unexpected Error',
  userMessage: 'An unexpected error occurred. Try again or contact support if the problem persists.',
  severity: 'error',
};

// Resolve an error detail string to descriptor (supports prefix match for config errors).
export function resolveError(detail: string | undefined | null): ErrorDescriptor {
  if (!detail) return FALLBACK_ERROR;
  if (ERROR_MAP[detail]) return ERROR_MAP[detail];
  if (detail.startsWith('invalid configuration:')) return ERROR_MAP['invalid configuration:'];
  return FALLBACK_ERROR;
}
