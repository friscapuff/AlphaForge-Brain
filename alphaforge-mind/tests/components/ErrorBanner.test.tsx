/// <reference types="vitest" />
import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { vi } from 'vitest';
import { useErrorStore } from '../../src/state/errors.js';
import ErrorBanner from '../../src/components/ErrorBanner.js';
import { ERROR_MAP } from '../../src/errors/errorMessages.js';

function setMockError(partial: any) {
  const base = {
    descriptor: ERROR_MAP['rate limit exceeded'],
    correlationId: 'cid-123',
    rateLimitResetMs: Date.now() + 2500, // 2.5s
    retryable: true,
    rawDetail: 'rate limit exceeded',
  };
  useErrorStore.getState().setError({ ...base, ...partial });
}

describe('ErrorBanner', () => {
  test('renders rate limit countdown and correlation id', () => {
    setMockError({});
    render(<ErrorBanner />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Too Many Requests/)).toBeInTheDocument();
    expect(screen.getByText(/Correlation: cid-123/)).toBeInTheDocument();
  });

  test('counts down to retry', () => {
    vi.useFakeTimers();
    setMockError({ rateLimitResetMs: Date.now() + 1100 });
    render(<ErrorBanner />);
    expect(screen.getByText(/Rate limit resets in/)).toBeInTheDocument();
    act(() => { vi.advanceTimersByTime(1200); });
    expect(screen.getByText(/You can retry now/)).toBeInTheDocument();
    vi.useRealTimers();
  });

  test('dismiss clears banner', () => {
    setMockError({});
    render(<ErrorBanner />);
    const btn = screen.getByRole('button', { name: /Dismiss error/i });
    act(() => { btn.click(); });
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
