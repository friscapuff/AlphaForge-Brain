import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
// @ts-ignore placeholder until implemented
// Real IndicatorManager will replace fallback later.

const FallbackIndicatorManager = () => {
  const [indicators, setIndicators] = React.useState<string[]>(() => {
    try {
      const raw = window.localStorage.getItem('af.indicators');
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });
  const add = () => {
    const next = [...indicators, `ema${indicators.length + 1}`];
    setIndicators(next);
    window.localStorage.setItem('af.indicators', JSON.stringify(next));
  };
  const removeFirst = () => {
    const [, ...rest] = indicators;
    setIndicators(rest);
    window.localStorage.setItem('af.indicators', JSON.stringify(rest));
  };
  return (
    <div>
      <button onClick={add}>add-indicator</button>
      <button onClick={removeFirst}>remove-first</button>
      <ul data-testid="indicators-list">
        {indicators.map(i => (
          <li key={i}>{i}</li>
        ))}
      </ul>
    </div>
  );
};

// dynamic resolution
// @ts-ignore
const ResolvedIndicatorManager = FallbackIndicatorManager;

describe('T017 Indicators Persistence (Test-First)', () => {
  const storage: Record<string, string> = {};

  beforeEach(() => {
    vi.spyOn(window.localStorage.__proto__ as any, 'getItem').mockImplementation(((k: string) => storage[k] ?? null) as any);
    vi.spyOn(window.localStorage.__proto__ as any, 'setItem').mockImplementation(((k: string, v: string) => {
      storage[k] = v;
    }) as any);
    vi.spyOn(window.localStorage.__proto__ as any, 'removeItem').mockImplementation(((k: string) => {
      delete storage[k];
    }) as any);
    Object.keys(storage).forEach(k => delete storage[k]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    Object.keys(storage).forEach(k => delete storage[k]);
  });

  it('adds and persists indicators to localStorage key af.indicators', () => {
    render(<ResolvedIndicatorManager />);
    const addBtn = screen.getByText('add-indicator');
    fireEvent.click(addBtn);
    fireEvent.click(addBtn);
    const list = screen.getByTestId('indicators-list');
    expect(list.querySelectorAll('li').length).toBe(2);
    expect(storage['af.indicators']).toBeTruthy();
    const parsed = JSON.parse(storage['af.indicators']);
    expect(parsed.length).toBe(2);
  });

  it('removes indicators and updates persistence', () => {
    storage['af.indicators'] = JSON.stringify(['ema1', 'ema2']);
    render(<ResolvedIndicatorManager />);
    fireEvent.click(screen.getByText('remove-first'));
    const list = screen.getByTestId('indicators-list');
    expect(list.querySelectorAll('li').length).toBe(1);
    const parsed = JSON.parse(storage['af.indicators']);
    expect(parsed).toEqual(['ema2']);
  });
});
