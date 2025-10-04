import { describe, it, expect } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BacktestForm } from '../../src/components/backtest/BacktestForm.js';

/**
 * T093: Keyboard navigation (tab order) through strategy form.
 * Acceptance: Sequential Tab presses move focus through inputs in logical order then to submit button.
 */

describe('T093 BacktestForm keyboard navigation', () => {
  it('tabs through fields in order start -> end -> strategy -> equity -> submit', async () => {
    const user = (userEvent as any).setup();
    render(<BacktestForm onSubmit={() => { /* noop */ }} />);

    const start = screen.getByPlaceholderText('start');
    const end = screen.getByPlaceholderText('end');
    const strategy = screen.getByPlaceholderText('strategy name');
    const equity = screen.getByPlaceholderText('initial equity');
    const submit = screen.getByText('run-backtest');

    // Initially focus first element via tab (jsdom doesn't auto-focus form first control)
    await user.tab();
    expect(start).toHaveFocus();

    await user.tab();
    expect(end).toHaveFocus();

    await user.tab();
    expect(strategy).toHaveFocus();

    await user.tab();
    expect(equity).toHaveFocus();

    await user.tab();
    expect(submit).toHaveFocus();
  });
});
