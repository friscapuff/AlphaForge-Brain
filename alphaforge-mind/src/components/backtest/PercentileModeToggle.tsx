import React from 'react';
import { useFeatureFlags } from '../../state/featureFlags.js';

/**
 * PercentileModeToggle (T046)
 * Shown only when extendedPercentiles flag is true. For now it is a placeholder
 * that would eventually allow switching between baseline and extended percentile sets.
 */
export const PercentileModeToggle: React.FC = () => {
  const { extendedPercentiles } = useFeatureFlags();
  if (!extendedPercentiles) return null;
  return (
    <div className="text-xs flex items-center gap-2 border rounded px-2 py-1 border-neutral-700">
      <span className="font-medium">Percentiles:</span>
      <button type="button" className="px-1 py-0.5 bg-neutral-800 rounded border border-neutral-600">Baseline</button>
      <button type="button" className="px-1 py-0.5 bg-neutral-900 rounded border border-neutral-700">Extended</button>
      <span className="text-neutral-500">(placeholder)</span>
    </div>
  );
};
