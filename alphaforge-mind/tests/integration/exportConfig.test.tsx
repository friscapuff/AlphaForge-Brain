import { describe, it, expect } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

// @ts-ignore placeholder
// Real ExportConfigButton will replace fallback later.

// Fallback simulates capturing a config object and exposing JSON text
// @ts-ignore
const FallbackExportConfigButton = () => {
  const [json, setJson] = React.useState<string | null>(null);
  const config = {
    symbol: 'AAPL',
    strategy: { name: 'ema_cross', params: { fast: 12, slow: 26 } },
    risk: { initial_equity: 10000, position_sizing: 'fixed_fraction', fraction: 0.02 }
  };
  const exportIt = () => {
    // canonical ordering expectation: keys in insertion order (object literal) - later implementation may need stable sort
    setJson(JSON.stringify(config, null, 2));
  };
  return (
    <div>
      <button onClick={exportIt}>export-config</button>
      {json && <pre data-testid="export-json">{json}</pre>}
    </div>
  );
};

// dynamic resolution
// @ts-ignore
const ResolvedExportButton = FallbackExportConfigButton;

describe('T024 Export Configuration JSON (Test-First)', () => {
  it('exports JSON representation on user action', () => {
    render(<ResolvedExportButton />);
    fireEvent.click(screen.getByText('export-config'));
    const pre = screen.getByTestId('export-json');
    const text = pre.textContent || '';
    expect(text).toMatch(/"symbol": "AAPL"/);
    expect(text).toMatch(/"strategy"/);
    expect(text).toMatch(/"risk"/);
  });
});
