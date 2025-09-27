import React from 'react';
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { useFeatureFlags } from '../../../src/state/featureFlags.js';
import { PercentileModeToggle } from '../../../src/components/backtest/PercentileModeToggle.js';
import { AdvancedValidationToggles } from '../../../src/components/backtest/AdvancedValidationToggles.js';

// Helper to mutate flags inside test context
function setFlag<K extends 'extendedPercentiles'|'advancedValidation'>(k: K, v: boolean) {
  useFeatureFlags.getState().setFlag(k, v);
}

describe('Feature flag gated components', () => {
  it('PercentileModeToggle hidden when flag off, visible when on', () => {
    setFlag('extendedPercentiles', false);
    let { queryByText, rerender } = render(<PercentileModeToggle />);
    expect(queryByText(/Percentiles:/)).toBeNull();
    setFlag('extendedPercentiles', true);
    rerender(<PercentileModeToggle />);
    expect(queryByText(/Percentiles:/)).not.toBeNull();
  });

  it('AdvancedValidationToggles hidden when flag off, visible when on', () => {
    setFlag('advancedValidation', false);
    let { queryByText, rerender } = render(<AdvancedValidationToggles />);
    expect(queryByText(/Advanced Validation:/)).toBeNull();
    setFlag('advancedValidation', true);
    rerender(<AdvancedValidationToggles />);
    expect(queryByText(/Advanced Validation:/)).not.toBeNull();
  });
});
