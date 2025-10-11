import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

import { trustGateRunPayload } from '../fixtures/trustGatePayload.js';

const suite = trustGateRunPayload.trust_gate;

describe('T022 Trust Gate badges render pass/fail/waived states', () => {
  it('renders badges for each gate with status indicators and correlation ids', async () => {
    // @ts-ignore trust gate badge component not implemented yet
    const module = await import('../../src/components/TrustGateBadge.js');
    const TrustGateBadge = module.TrustGateBadge ?? module.default;
    expect(TrustGateBadge).toBeTruthy();

    render(<TrustGateBadge suite={suite} />);

    for (const gate of suite.gates) {
      expect(screen.getByText(gate.name).textContent).toContain(gate.name);
      expect(screen.getByText(gate.status).textContent).toContain(gate.status);
      expect(
        screen.getByText(gate.correlation_id).textContent,
      ).toContain(gate.correlation_id);
    }
  });
});
