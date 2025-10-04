import { useState, useCallback, useRef, useEffect } from 'react';
import { useAppStore } from '../state/store.js';
import { useFeatureFlags } from '../state/featureFlags.js';
import { useUIStore } from '../state/ui.js';
import { apiClient } from '../services/api/client.js';

/**
 * useBacktestRun (T036)
 * Handles submission and polling life-cycle.
 * For now uses mock fetch placeholders until backend endpoints exist.
 */

export interface SubmitBacktestPayload {
  start: string; end: string; strategy: string; equity: number;
}

export interface UseBacktestRunReturn {
  status: string;
  submit: (payload: SubmitBacktestPayload) => Promise<void>;
  poll: () => Promise<void>;
  lastRunId?: string;
}

export function useBacktestRun(): UseBacktestRunReturn {
  const addRun = useAppStore(s => s.addRun);
  const setResult = useAppStore(s => s.setResult);
  const selectRun = useAppStore(s => s.selectRun);
  const [status, setStatus] = useState<string>('idle');
  const [lastRunId, setLastRunId] = useState<string | undefined>();
  const slowNoticeShown = useUIStore(s => s.slowNoticeShown);
  const showSlowNotice = useUIStore(s => s.showSlowNotice);
  const resetSlowNotice = useUIStore(s => s.resetSlowNotice);
  const slowTimerRef = useRef<number | null>(null);
  const envThreshold = (import.meta as any).env?.VITE_SLOW_RUN_MS;
  const SLOW_THRESHOLD_MS = typeof envThreshold === 'string' && /^\d+$/.test(envThreshold)
    ? parseInt(envThreshold, 10)
    : 5000; // default 5s

  const submit = useCallback(async (payload: SubmitBacktestPayload) => {
    const runId = `run_${Date.now()}`;
    addRun({ runId, status: 'queued', createdAt: new Date().toISOString() });
    selectRun(runId);
    setLastRunId(runId);
    const flags = useFeatureFlags.getState();
    // Persist last request for export modal
    (useAppStore.getState() as any).setLastRequest({
      start: payload.start,
      end: payload.end,
      strategy: payload.strategy,
      equity: payload.equity,
      flags: { extendedPercentiles: flags.extendedPercentiles, advancedValidation: flags.advancedValidation }
    });
    setStatus('queued');
    resetSlowNotice();
    if (slowTimerRef.current) window.clearTimeout(slowTimerRef.current);
    slowTimerRef.current = window.setTimeout(() => {
      if (!slowNoticeShown) {
        showSlowNotice();
        // eslint-disable-next-line no-console
        console.warn('[Backtest] Run still processing (>5s)');
      }
    }, SLOW_THRESHOLD_MS);
  }, [addRun, selectRun, resetSlowNotice, showSlowNotice, slowNoticeShown]);

  const poll = useCallback(async () => {
    if (!lastRunId) return;
    const current = status;
    if (current === 'queued') {
      setStatus('running');
    } else if (current === 'running') {
      setStatus('completed');
      const flags = useFeatureFlags.getState();
      setResult(lastRunId, {
        equityCurve: [
          { t: new Date(Date.now() - 60000).toISOString(), equity: 10000 },
          { t: new Date().toISOString(), equity: 10025 }
        ],
        metrics: { cagr: 0.12, sharpe: 1.4 },
        // Basic demo: if advancedValidation is enabled, return a caution flag with two metrics.
        // In real integration, these would be returned from backend API payload (T042).
        validationCaution: flags.advancedValidation ? true : false,
        validationCautionMetrics: flags.advancedValidation ? ['permutation.p', 'block_bootstrap.p'] : [],
      });
      if (slowTimerRef.current) {
        window.clearTimeout(slowTimerRef.current);
        slowTimerRef.current = null;
      }
    }
  }, [lastRunId, status, setResult]);

  useEffect(() => () => {
    if (slowTimerRef.current) window.clearTimeout(slowTimerRef.current);
  }, []);

  return { status, submit, poll, lastRunId };
}

export default useBacktestRun;
