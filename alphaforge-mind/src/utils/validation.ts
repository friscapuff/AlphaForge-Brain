/**
 * validation.ts (T035)
 * Central backtest form validation utilities.
 * Mirrors rules expressed in integration test T018 and FR-004.
 */

export interface BacktestFormInput {
  start: string;
  end: string;
  strategy: string;
  equity: number | string;
}

export interface ValidationIssue { field: keyof BacktestFormInput | 'equity'; message: string; }

export interface ValidationResult {
  ok: boolean;
  issues: ValidationIssue[];
}

export function validateBacktestInput(input: BacktestFormInput): ValidationResult {
  const issues: ValidationIssue[] = [];
  const { start, end, strategy } = input;
  const equityNum = typeof input.equity === 'string' ? parseFloat(input.equity) : input.equity;
  if (!start) issues.push({ field: 'start', message: 'start required' });
  if (!end) issues.push({ field: 'end', message: 'end required' });
  if (!strategy) issues.push({ field: 'strategy', message: 'strategy required' });
  if (!(equityNum > 0)) issues.push({ field: 'equity', message: 'equity must be > 0' });
  return { ok: issues.length === 0, issues };
}

export function canonicalizeBacktestInput(input: BacktestFormInput): BacktestFormInput & { equity: number } {
  const equityNum = typeof input.equity === 'string' ? parseFloat(input.equity) : input.equity;
  return { ...input, equity: equityNum };
}
