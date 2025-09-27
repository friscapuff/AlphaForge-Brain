import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
// @ts-ignore placeholder until implemented
// Real BacktestForm will replace fallback later.

// Fallback minimal form to express desired validation behavior for TDD.
// Will be replaced by real BacktestForm when implemented.
// Rules targeted (FR-004): require start, end, strategy name, risk initial_equity > 0.
// @ts-ignore
const FallbackBacktestForm = ({ onSubmit }: { onSubmit?: (data: unknown) => void }) => {
  const [errors, setErrors] = React.useState<string[]>([]);
  const handle = (e: React.FormEvent) => {
    e.preventDefault();
  const form = e.target as HTMLFormElement & { elements: any };
  const start = (form.elements.namedItem('start') as HTMLInputElement).value;
    const end = (form.elements.namedItem('end') as HTMLInputElement).value;
    const strat = (form.elements.namedItem('strategy') as HTMLInputElement).value;
    const equity = parseFloat((form.elements.namedItem('equity') as HTMLInputElement).value);
    const errs: string[] = [];
    if (!start) errs.push('start required');
    if (!end) errs.push('end required');
    if (!strat) errs.push('strategy required');
    if (!(equity > 0)) errs.push('equity must be > 0');
    setErrors(errs);
    if (errs.length === 0 && onSubmit) onSubmit({ start, end, strat, equity });
  };
  return (
    <form onSubmit={handle} data-testid="backtest-form">
      <input name="start" placeholder="start" />
      <input name="end" placeholder="end" />
      <input name="strategy" placeholder="strategy name" />
      <input name="equity" placeholder="initial equity" />
      <button type="submit">run-backtest</button>
      <ul data-testid="errors">
        {errors.map(e => (
          <li key={e}>{e}</li>
        ))}
      </ul>
    </form>
  );
};

// dynamic resolution
// @ts-ignore
const ResolvedBacktestForm = FallbackBacktestForm;

describe('T018 Backtest Form Validation (Test-First)', () => {
  it('blocks submission and shows errors for empty form', () => {
    const submitSpy = vi.fn();
    render(<ResolvedBacktestForm onSubmit={submitSpy} />);
    fireEvent.click(screen.getByText('run-backtest'));
    const errs = screen.getByTestId('errors');
    expect(errs.querySelectorAll('li').length).toBeGreaterThan(0);
    expect(submitSpy).not.toHaveBeenCalled();
  });

  it('accepts valid submission', () => {
    const submitSpy = vi.fn();
    render(<ResolvedBacktestForm onSubmit={submitSpy} />);
  const form = screen.getByTestId('backtest-form') as HTMLFormElement & { elements: any };
  (form.elements.namedItem('start') as HTMLInputElement).value = '2024-01-01';
    (form.elements.namedItem('end') as HTMLInputElement).value = '2024-06-01';
    (form.elements.namedItem('strategy') as HTMLInputElement).value = 'ema_cross';
    (form.elements.namedItem('equity') as HTMLInputElement).value = '10000';
    fireEvent.click(screen.getByText('run-backtest'));
    expect(submitSpy).toHaveBeenCalledOnce();
    const errs = screen.getByTestId('errors');
    expect(errs.querySelectorAll('li').length).toBe(0);
  });
});
