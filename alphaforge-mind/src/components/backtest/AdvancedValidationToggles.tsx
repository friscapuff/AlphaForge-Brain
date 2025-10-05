import React from 'react';
import { useFeatureFlags } from '../../state/featureFlags.js';

/**
 * AdvancedValidationToggles (T047)
 * Displayed only if advancedValidation flag is true. Placeholder for future
 * advanced validation modes (e.g., sensitivity, regime flags, etc.).
 */
export const AdvancedValidationToggles: React.FC = () => {
  const { advancedValidation } = useFeatureFlags();
  if (!advancedValidation) return null;
  return (
    <div className="text-xs flex items-center gap-2 border rounded px-2 py-1 border-neutral-700">
      <span className="font-medium">Advanced Validation:</span>
      <label className="flex items-center gap-1"><input type="checkbox" disabled /> Sensitivity</label>
      <label className="flex items-center gap-1"><input type="checkbox" disabled /> Regime Flags</label>
      <span className="text-neutral-500">(placeholder)</span>
    </div>
  );
};
