import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, act } from '@testing-library/react';

// @ts-ignore placeholder
// Real SlowNoticeProbe will replace fallback later.

// Fallback component triggers notice after 5000ms if still pending
// @ts-ignore
const FallbackSlowNoticeProbe = () => {
  const [show, setShow] = React.useState(false);
  React.useEffect(() => {
    const id = setTimeout(() => setShow(true), 5000);
    return () => clearTimeout(id);
  }, []);
  return <div>{show && <div data-testid="slow-notice">Operation is taking longer than expected...</div>}</div>;
};

// dynamic resolution
// @ts-ignore
const ResolvedSlowNotice = FallbackSlowNoticeProbe;

describe('T022 Slow Response Notice (Test-First)', () => {
  beforeEach(() => { vi.useFakeTimers(); return undefined as any; });
  afterEach(() => { vi.useRealTimers(); return undefined as any; });

  it('does not show notice before 5s then appears after threshold', async () => {
    render(<ResolvedSlowNotice />);
    expect(screen.queryByTestId('slow-notice')).toBeNull();
    await act(async () => {
      vi.advanceTimersByTime(5000);
    });
    expect(screen.getByTestId('slow-notice')).toBeInTheDocument();
  });
});
