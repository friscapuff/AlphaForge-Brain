import React from 'react';
import { useAppStore } from '../../state/store.js';
import { canonicalRoundTrip } from '../../utils/canonicalJson.js';
import { callCanonicalHash } from '../../services/api/canonical.js';

/** ExportConfigModal (T045) */
export interface ExportConfigModalProps {
  open: boolean;
  onClose: () => void;
}

export function ExportConfigModal({ open, onClose }: ExportConfigModalProps): React.ReactElement | null {
  const selected = useAppStore(s => s.selectedRunId);
  const run = useAppStore(s => s.runs.find(r => r.runId === selected));
  const lastRequest = useAppStore(s => s.lastRequest);
  if (!open) return null;
  // Build export object – includes placeholders until full payload (date range, validation toggles) is wired into store
  const data = run ? {
    runId: run.runId,
    createdAt: run.createdAt,
    strategy: { id: 'buy_hold', version: 'v1', params: [] },
    risk: { position_size_pct: 100, stop_type: 'none' },
    dateRange: lastRequest ? { start: lastRequest.start, end: lastRequest.end } : null,
    validation: lastRequest ? {
      extendedPercentiles: lastRequest.flags.extendedPercentiles,
      advancedValidation: lastRequest.flags.advancedValidation,
    } : null,
  } : null;
  const [exportState, setExportState] = React.useState<{ json: string; hash: string; valid: boolean } | null>(null);
  const [verifyState, setVerifyState] = React.useState<
    | { status: 'idle' }
    | { status: 'verifying' }
    | { status: 'success'; serverHash: string; serverCanonical: string; match: boolean }
    | { status: 'error'; message: string }
  >({ status: 'idle' });
  const [copied, setCopied] = React.useState<'json' | 'hash' | null>(null);
  const doCopy = async (kind: 'json' | 'hash') => {
    const text = kind === 'json' ? (exportState?.json ?? '') : (exportState?.hash ?? '');
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const ta = document.createElement('textarea');
        ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
      }
      setCopied(kind);
      setTimeout(() => setCopied(null), 1500);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('Copy failed', e);
    }
  };
  React.useEffect(() => {
    let mounted = true;
    if (data) {
      canonicalRoundTrip(data).then(r => { if (mounted) setExportState(r); });
    } else {
      setExportState(null);
    }
    return () => { mounted = false; };
  }, [selected, open]);
  const json = exportState?.json ?? 'null';
  const doVerify = async () => {
    if (!data || !exportState || verifyState.status === 'verifying') return;
    setVerifyState({ status: 'verifying' });
    try {
      const res = await callCanonicalHash(data);
      setVerifyState({
        status: 'success',
        serverHash: res.sha256,
        serverCanonical: res.canonical,
        match: res.sha256 === exportState.hash,
      });
    } catch (e: any) {
      setVerifyState({ status: 'error', message: e?.message || 'verify failed' });
    }
  };
  return React.createElement(
    'div',
    { className: 'fixed inset-0 bg-black/60 flex items-center justify-center z-50' },
    React.createElement(
      'div',
      { className: 'bg-neutral-900 border border-neutral-700 p-4 rounded w-80 space-y-2 text-xs' },
      React.createElement('div', { className: 'font-semibold text-sm' }, 'Export Configuration'),
      React.createElement('div', { className: 'flex flex-col gap-1' },
        React.createElement('pre', { className: 'bg-neutral-950 p-2 rounded border border-neutral-800 overflow-x-auto max-h-60' }, json),
        exportState && React.createElement('div', { className: 'font-mono break-all text-[10px] text-neutral-400 flex flex-col gap-1' },
          React.createElement('span', null, 'sha256: ' + exportState.hash),
          React.createElement('div', { className: 'flex gap-2' },
            React.createElement('button', { type: 'button', onClick: () => doCopy('json'), className: 'px-2 py-0.5 border border-neutral-700 rounded bg-neutral-800 hover:bg-neutral-700 transition text-[10px]' }, copied==='json' ? 'Copied JSON' : 'Copy JSON'),
            React.createElement('button', { type: 'button', onClick: () => doCopy('hash'), className: 'px-2 py-0.5 border border-neutral-700 rounded bg-neutral-800 hover:bg-neutral-700 transition text-[10px]' }, copied==='hash' ? 'Copied Hash' : 'Copy Hash')
          ),
          React.createElement('div', { className: 'text-[10px] ' + (exportState.valid ? 'text-emerald-400' : 'text-red-400') }, exportState.valid ? 'round-trip: stable' : 'round-trip: mismatch'),
          React.createElement('div', { className: 'flex gap-2 items-center flex-wrap' },
            React.createElement('button', { type: 'button', onClick: doVerify, disabled: verifyState.status === 'verifying', className: 'px-2 py-0.5 border border-neutral-700 rounded bg-neutral-800 hover:bg-neutral-700 disabled:opacity-50 transition text-[10px]' }, verifyState.status === 'verifying' ? 'Verifying…' : 'Verify'),
            verifyState.status === 'success' && React.createElement('span', { className: 'text-[10px] ' + (verifyState.match ? 'text-emerald-400' : 'text-red-400') }, verifyState.match ? 'server match' : 'server mismatch'),
            verifyState.status === 'error' && React.createElement('span', { className: 'text-red-400' }, 'verify error')
          ),
          verifyState.status === 'success' && !verifyState.match && React.createElement('details', { className: 'mt-1' },
            React.createElement('summary', { className: 'cursor-pointer select-none text-neutral-500' }, 'Server canonical diff view'),
            React.createElement('pre', { className: 'bg-neutral-950 p-2 mt-1 rounded border border-neutral-800 overflow-x-auto max-h-40' }, verifyState.serverCanonical)
          )
        )
      ),
      React.createElement(
        'button',
        { type: 'button', onClick: onClose, className: 'px-2 py-1 rounded bg-neutral-800 border border-neutral-700 w-full' },
        'Close'
      )
    )
  );
}
export default ExportConfigModal;
