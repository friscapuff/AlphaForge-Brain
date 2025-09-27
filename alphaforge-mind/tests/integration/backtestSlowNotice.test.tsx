import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, act } from '@testing-library/react';
import { useBacktestRun } from '../../src/hooks/useBacktestRun.js';
import { useUIStore } from '../../src/state/ui.js';

function TestHarness() {
  const { submit, status, poll } = useBacktestRun();
  // expose on window for manual debug
  // @ts-ignore
  window.__poll = poll;
  return <button onClick={() => submit({ start: '2024-01-01', end: '2024-01-31', strategy: 'buy_hold', equity: 10000 })}>{status}</button>;
}

describe('T089 slow notice single emission', () => {
  it('emits exactly one slow notice after 5s and not again after completion', async () => {
    vi.useFakeTimers();
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    render(<TestHarness />);

    // trigger submit
    const button = document.querySelector('button')!;
    act(() => {
      button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    // Advance to threshold (5000ms) -> notice fires exactly once
    act(() => { vi.advanceTimersByTime(5000); });
    expect(warnSpy).toHaveBeenCalledTimes(1);
    expect(useUIStore.getState().slowNoticeShown).toBe(true);

    // Advance further; ensure no duplicate
    act(() => { vi.advanceTimersByTime(10000); });
    expect(warnSpy).toHaveBeenCalledTimes(1);

    // Simulate poll leading to completion; timer cleared and still single emission
    act(() => { (window as any).__poll(); });
    act(() => { (window as any).__poll(); }); // ensure completion branch
    expect(warnSpy).toHaveBeenCalledTimes(1);

    warnSpy.mockRestore();
    vi.useRealTimers();
  });
});
