import React from 'react';
import { useAppStore } from '../../state/store.js';
import { ValidationOutputs } from '../validation/ValidationOutputs.js';

export function ValidationSummary(): React.ReactElement {
  const selectedRunId = useAppStore((s) => s.selectedRunId);
  const validation = useAppStore((s) => (selectedRunId ? s.results[selectedRunId]?.validation : undefined));
  const cautionMetrics = useAppStore((s) => (selectedRunId ? s.results[selectedRunId]?.validationCautionMetrics ?? [] : []));

  return (
    <ValidationOutputs
      runId={selectedRunId ?? undefined}
      validation={validation}
      cautionMetrics={cautionMetrics}
    />
  );
}

export default ValidationSummary;
