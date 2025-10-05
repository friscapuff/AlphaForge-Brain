import React from 'react';
import { useUIStore } from '../../state/ui.js';

export const SlowNotice: React.FC = () => {
  const shown = useUIStore(s => s.slowNoticeShown);
  const dismiss = useUIStore(s => s.dismissSlowNotice);
  if (!shown) return null;
  return (
    <div role="status" aria-live="polite" className="fixed bottom-4 right-4 max-w-sm bg-amber-900/90 border border-amber-500 text-amber-100 text-sm rounded shadow-lg p-3 backdrop-blur">
      <p className="font-semibold mb-1">Still working…</p>
      <p className="text-xs leading-snug mb-2">This backtest is taking longer than usual. Results will appear automatically when ready.</p>
      <button onClick={dismiss} className="text-xs px-2 py-1 bg-amber-700 hover:bg-amber-600 rounded border border-amber-400">Dismiss</button>
    </div>
  );
};

export default SlowNotice;
