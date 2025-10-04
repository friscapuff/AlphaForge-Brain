import { describe, it, expect } from 'vitest';
import React from 'react';
import { render } from '@testing-library/react';
import { BacktestValidationPage } from '../../src/pages/BacktestValidationPage.js';
import axe from 'axe-core';

/**
 * T092: Axe scan on BacktestValidationPage no critical violations
 * Acceptance: No violations with impact === 'critical'. We allow lesser severities for now but log them.
 */

describe('T092 BacktestValidationPage accessibility', () => {
  it('has no critical axe violations', async () => {
    // jsdom doesn't implement canvas; stub getContext to avoid axe-core noise from color contrast rule
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (HTMLCanvasElement.prototype as any).getContext = () => null;
    // Enable minimal rendering mode to skip heavy charts/canvas for the scan
    (document.body as any).dataset.minA11y = 'true';
    const { container } = render(<BacktestValidationPage />);
    const results = await axe.run(container as unknown as HTMLElement, {
      // Disable rules known to require landmark/structure decisions not yet finalized
      rules: {
        'region': { enabled: false }, // optional multiple region labeling improvements later
      },
    });

    // Collect critical violations (impact === 'critical')
  const critical = results.violations.filter((v: any) => v.impact === 'critical');

    if (critical.length > 0) {
      // Provide helpful debug output
  console.error('Critical accessibility violations:', critical.map((v: any) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length })));
    }

    expect(critical).toHaveLength(0);
  });
});
