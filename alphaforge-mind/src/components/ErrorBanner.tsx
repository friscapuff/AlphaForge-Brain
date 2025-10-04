import React, { useEffect, useMemo, useState } from 'react';
import { useErrorStore } from '../state/errors.js';
import { FALLBACK_ERROR } from '../errors/errorMessages.js';

// Basic inline styles; in real app could map to design system tokens
const baseStyle: React.CSSProperties = {
  fontFamily: 'system-ui, sans-serif',
  padding: '8px 12px',
  borderRadius: 4,
  margin: '8px 0',
  display: 'flex',
  flexDirection: 'row',
  alignItems: 'flex-start',
  gap: 12,
  fontSize: 14,
};

const severityColors: Record<string, { bg: string; border: string; fg: string }> = {
  info: { bg: '#eef6ff', border: '#5b9ded', fg: '#0b5394' },
  warn: { bg: '#fff8e1', border: '#e6b800', fg: '#8a6d00' },
  error: { bg: '#fdecea', border: '#e53935', fg: '#b71c1c' },
};

export const ErrorBanner: React.FC = () => {
  const errState = useErrorStore((s) => s.current);
  const clear = useErrorStore((s) => s.clear);
  const [now, setNow] = useState<number>(() => Date.now());

  // Timer always declared (stable hook order) but inert when no reset target
  useEffect(() => {
    if (!errState?.rateLimitResetMs) return; // inert when absent
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [errState?.rateLimitResetMs]);

  const remainingSec = useMemo(() => {
    if (!errState?.rateLimitResetMs) return undefined;
    return Math.max(0, Math.floor((errState.rateLimitResetMs - now) / 1000));
  }, [errState?.rateLimitResetMs, now]);

  if (!errState) return null; // after hooks to keep order stable
  const desc = errState.descriptor || FALLBACK_ERROR;
  const sev = desc.severity || 'error';
  const colors = severityColors[sev] || severityColors.error;
  const retryHint = errState.retryable === true || desc.severity === 'warn';

  return (
    <div role="alert" aria-live="polite" style={{ ...baseStyle, background: colors.bg, color: colors.fg, border: `1px solid ${colors.border}` }}>
      <div style={{ flex: 1 }}>
        <strong style={{ display: 'block', marginBottom: 4 }}>{desc.title}</strong>
        <div style={{ lineHeight: 1.4 }}>{desc.userMessage}</div>
        {retryHint && (
          <div style={{ marginTop: 6, fontSize: 12 }}>
            {remainingSec !== undefined && remainingSec > 0 ? (
              <span>Rate limit resets in {remainingSec}s…</span>
            ) : (
              <span>You can retry now.</span>
            )}
          </div>
        )}
        <div style={{ marginTop: 6, fontSize: 11, opacity: 0.7 }}>
          {errState.correlationId && <span>Correlation: {errState.correlationId}</span>}
          {errState.rawDetail && <span style={{ marginLeft: 8 }}>Detail: {errState.rawDetail}</span>}
        </div>
      </div>
      <button onClick={() => clear()} aria-label="Dismiss error" style={{ background: 'transparent', border: 'none', color: colors.fg, cursor: 'pointer', fontSize: 16, lineHeight: 1 }}>×</button>
    </div>
  );
};

export default ErrorBanner;
