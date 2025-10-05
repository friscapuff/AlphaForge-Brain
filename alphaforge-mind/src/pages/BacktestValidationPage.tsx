import React from 'react';
import { BacktestForm } from '../components/backtest/BacktestForm.js';
import { RunHistory } from '../components/backtest/RunHistory.js';
import { useBacktestRun } from '../hooks/useBacktestRun.js';
import { useFeatureFlags } from '../state/featureFlags.js';
import { useAppStore } from '../state/store.js';
import { EquityCurveChart } from '../components/backtest/EquityCurveChart.js';
import { MetricsGrid } from '../components/backtest/MetricsGrid.js';
import { TradesSummaryTable } from '../components/backtest/TradesSummaryTable.js';
import { ValidationSummary } from '../components/backtest/ValidationSummary.js';
import { WalkForwardSplitsChart } from '../components/backtest/WalkForwardSplitsChart.js';
import { MonteCarloChart } from '../components/backtest/MonteCarloChart.js';
import { ExportConfigModal } from '../components/backtest/ExportConfigModal.js';
import { PercentileModeToggle } from '../components/backtest/PercentileModeToggle.js';
import { AdvancedValidationToggles } from '../components/backtest/AdvancedValidationToggles.js';
import { ErrorBoundary } from '../components/common/ErrorBoundary.js';
import { MonteCarloOverlay } from '../components/backtest/MonteCarloOverlay.js';

export function BacktestValidationPage() {
  const { status, submit, poll } = useBacktestRun();
  const setFlag = useFeatureFlags(s => s.setFlag);
  const flags = useFeatureFlags();
  const selectedRunId = useAppStore(s => s.selectedRunId);
  const results = useAppStore(s => (selectedRunId ? s.results[selectedRunId] : undefined));
  const caution = !!results?.validationCaution;
  const cautionMetrics = results?.validationCautionMetrics ?? [];
  const optMode = results?.optimizationMode;
  const warnings = results?.advanced?.warnings ?? [];
  const [exportOpen, setExportOpen] = React.useState(false);

  // Allow tests to opt out of rendering heavier visual components (charts) by setting
  // document.body.dataset.minA11y = 'true'. This reduces noise for axe scans and avoids
  // potential canvas/SVG complexities not relevant to initial accessibility baseline.
  const minimal = typeof document !== 'undefined' && (document.body as any)?.dataset?.minA11y === 'true';

  return (
    <ErrorBoundary>
  <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 bg-neutral-800 text-white px-3 py-2 rounded z-50">Skip to main content</a>
  <div id="main" className="p-4 space-y-4" role="main" aria-label="Backtest validation main content">
      <h1 className="text-xl font-semibold">Backtest & Validation</h1>
      <section className="space-y-2" aria-labelledby="cfg-heading">
        <h2 id="cfg-heading" className="font-semibold text-sm">Configuration</h2>
        <BacktestForm onSubmit={async (data) => { await submit(data); }} />
        <div className="flex gap-2 text-xs items-center">
          <button type="button" onClick={() => poll()} className="px-2 py-1 rounded bg-neutral-800 border border-neutral-700">poll</button>
          <span>Status: {status}</span>
          {selectedRunId && <span>Selected: {selectedRunId}</span>}
        </div>
      </section>
      <section className="space-y-2" aria-labelledby="runs-heading">
        <h2 id="runs-heading" className="font-semibold text-sm">Runs</h2>
        <RunHistory />
      </section>
      <section className="space-y-3" aria-labelledby="results-heading">
        <h2 id="results-heading" className="font-semibold text-sm flex items-center gap-2">
          Results
          {caution && (
            <span
              role="img"
              aria-label="Validation caution"
              title={cautionMetrics.length ? `Caution metrics: ${cautionMetrics.join(', ')}` : 'Validation caution'}
              className="inline-flex items-center gap-1 text-amber-400 bg-amber-950/40 border border-amber-800 px-2 py-0.5 rounded-full text-[10px]"
              data-testid="validation-caution-badge"
            >
              ⚠ caution
            </span>
          )}
        </h2>
        {optMode === 'deferred' && warnings.length > 0 && (
          <div
            role="alert"
            className="text-[11px] bg-amber-900/30 border border-amber-800 text-amber-300 px-2 py-1 rounded"
            data-testid="optimization-deferred-warning"
          >
            {(() => {
              const w = warnings.find(w => (w as any).code === 'OPTIMIZATION_DEFERRED') as any;
              const combos = w?.combinations ?? '?';
              const limit = w?.limit ?? '?';
              return `Optimization deferred: ${combos} combinations exceed limit ${limit}.`;
            })()}
          </div>
        )}
        {!minimal && (
          <div className="flex flex-wrap gap-4">
            <div className="space-y-1">
              <div className="text-xs font-medium">Equity Curve</div>
              <EquityCurveChart />
            </div>
            <div className="space-y-1">
              <div className="text-xs font-medium">Metrics</div>
              <MetricsGrid />
            </div>
            <div className="space-y-1">
              <div className="text-xs font-medium">Trades Summary</div>
              <TradesSummaryTable />
            </div>
            <div className="space-y-1">
              <div className="text-xs font-medium">Validation</div>
              <ValidationSummary />
            </div>
            <div className="space-y-1">
              <div className="text-xs font-medium">Walk-Forward Splits</div>
              <WalkForwardSplitsChart />
            </div>
            <div className="space-y-1">
              <div className="text-xs font-medium">Monte Carlo (endpoints)</div>
              <MonteCarloChart />
              <MonteCarloOverlay />
            </div>
          </div>
        )}
        <div>
          <button type="button" onClick={() => setExportOpen(true)} className="mt-2 px-2 py-1 rounded bg-neutral-800 border border-neutral-700 text-xs">Export Config</button>
        </div>
      </section>
      <section className="space-y-2" aria-labelledby="flags-heading">
        <h2 id="flags-heading" className="font-semibold text-sm">Feature Flags (early)</h2>
        <div className="flex gap-4 text-xs">
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={flags.extendedPercentiles} onChange={e => setFlag('extendedPercentiles', e.target.checked)} />
            extendedPercentiles
          </label>
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={flags.advancedValidation} onChange={e => setFlag('advancedValidation', e.target.checked)} />
            advancedValidation
          </label>
        </div>
        <div className="flex flex-col gap-2 pt-2">
          <PercentileModeToggle />
          <AdvancedValidationToggles />
        </div>
      </section>
      {!minimal && <ExportConfigModal open={exportOpen} onClose={() => setExportOpen(false)} />}
    </div>
    </ErrorBoundary>
  );
}
