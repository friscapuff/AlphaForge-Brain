import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { ValidationOutputs } from '../../../src/components/validation/ValidationOutputs.js';
import type { ValidationData } from '../../../src/services/api/backtests.js';

const validationFixture: ValidationData = {
  schemaVersion: 2,
  significanceStatus: 'pass',
  config: {
    modules: [
      { id: 'permutation', label: 'Permutation', enabled: true },
      { id: 'dsr', label: 'Deflated Sharpe', enabled: true },
      { id: 'psr', label: 'Probabilistic Sharpe', enabled: false },
      { id: 'purged_kfold', label: 'Purged K-Fold', enabled: true },
      { id: 'cpcv', label: 'CPCV', enabled: true },
      { id: 'realism', label: 'Execution Realism', enabled: true },
    ],
    permutationCount: 500,
    significanceThreshold: 0.01,
    leakageThreshold: 0.1,
    realismCapacityBpsLimit: 450,
    biasAbsoluteThreshold: 0.25,
    biasRelativeThreshold: 0.5,
  },
  permutation: {
    segments: [
      {
        segmentId: 'in_sample',
        pValue: 0.0042,
        effectSize: 1.8,
        observedMetric: 1.23,
        executedPermutations: 480,
        requestedPermutations: 500,
        histogramSummary: {
          mean: 0.98,
          stdDev: 0.12,
          percentiles: [
            { percentile: 5, value: -0.2 },
            { percentile: 50, value: 0.8 },
            { percentile: 95, value: 1.6 },
          ],
        },
        artifactPath: 'validation/permutation/segment_in_sample.parquet',
      },
      {
        segmentId: 'walk_forward_1',
        pValue: 0.028,
        effectSize: 1.1,
        observedMetric: 0.87,
        executedPermutations: 470,
        requestedPermutations: 500,
        fallbackReason: 'insufficient_samples',
      },
    ],
  },
  biasAdjustments: {
    status: 'pass',
    observedSharpe: 1.95,
    deflatedSharpe: 1.62,
    probabilisticSharpe: 0.987,
    assumedTrials: 120,
    benchmarkSharpe: 0.5,
    skewness: -0.2,
    kurtosis: 3.1,
  },
  crossValidation: {
    mode: 'cpcv',
    leakageScore: 0.04,
    biasFlag: false,
    folds: [
      {
        foldId: 'F01',
        trainRange: { start: '2018-01-01', end: '2019-12-31' },
        testRange: { start: '2020-01-01', end: '2020-03-31' },
        purgeSpan: '30D',
        metrics: { sharpe: 1.45, totalReturn: 0.12 },
      },
      {
        foldId: 'F02',
        trainRange: { start: '2018-04-01', end: '2020-06-30' },
        testRange: { start: '2020-07-01', end: '2020-09-30' },
        purgeSpan: '30D',
        metrics: { sharpe: 1.51, totalReturn: 0.09 },
      },
    ],
  },
  executionRealism: {
    status: 'caution',
    transactionCostBps: 35,
    marketImpactBps: 20,
    capacityRatio: 0.82,
    warnings: ['Capacity ratio exceeds guidance band.'],
    guidance: ['Maintain participation rate below 10% to preserve capacity buffer.'],
    assumptions: { participation: '0.08', decay: '30m' },
  },
  failedChecks: ['cross_validation'],
  cautionChecks: ['permutation_sampling'],
  metadata: {
    leakage_threshold: 0.1,
    permutation_shortfalls: [{ segment_id: 'walk_forward_1', requested: 500, executed: 470 }],
    realism_status: 'caution',
  },
  manifestHash: 'deadbeef1234567890deadbeef1234567890deadbeef1234567890deadbeef1234',
  artifacts: [
    {
      path: 'validation/permutation/segment_in_sample.parquet',
      size: 16384,
      sha256: '111122223333444455556666777788889999aaaabbbbccccddddeeeeffff0000',
    },
    {
      path: 'validation/realism.json',
      size: 2048,
      sha256: 'abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789',
    },
  ],
};

describe('ValidationOutputs component', () => {
  it('renders run identifier and caution metrics when provided', () => {
    render(
      <ValidationOutputs
        runId="run-123"
        validation={validationFixture}
        cautionMetrics={['permutation.walk_forward_1', 'execution_realism.warnings']}
      />
    );

    expect(screen.getByTestId('validation-run-id')).toHaveTextContent('run-123');
    expect(screen.getByTestId('validation-caution-metrics')).toHaveTextContent('permutation.walk_forward_1');
    expect(screen.getByTestId('validation-manifest-hash')).toHaveTextContent('deadbeef1234567890');
    expect(screen.getByTestId('validation-failed-checks')).toHaveTextContent('cross_validation');
    expect(screen.getByTestId('validation-caution-checks')).toHaveTextContent('permutation_sampling');
  });

  it('renders permutation segments with status badges and histogram summary', () => {
    render(<ValidationOutputs validation={validationFixture} />);

    const list = screen.getByTestId('validation-permutation-list');
    const firstItem = within(list).getByTestId('validation-permutation-in_sample');
    expect(within(firstItem).getByText('p-value')).toBeInTheDocument();
    expect(within(firstItem).getByTestId('validation-status-badge')).toHaveTextContent('pass');
    expect(within(firstItem).getByText(/Histogram summary/i)).toBeInTheDocument();
  expect(within(firstItem).getByText(/Observed metric/i)).toBeInTheDocument();

    const secondItem = within(list).getByTestId('validation-permutation-walk_forward_1');
    expect(within(secondItem).getByTestId('validation-status-badge')).toHaveTextContent('caution');
    expect(within(secondItem).getByText(/Fallback:/i)).toHaveTextContent('insufficient samples');
  });

  it('surfaces bias adjustments and module toggles', () => {
    render(<ValidationOutputs validation={validationFixture} />);

    expect(screen.getByText('1.950')).toBeInTheDocument();
    expect(screen.getByText('1.620')).toBeInTheDocument();

    const moduleToggle = screen.getByTestId('validation-module-psr');
    expect(moduleToggle).toHaveTextContent('off');
  });

  it('shows cross-validation fold table and leakage threshold details', () => {
    render(<ValidationOutputs validation={validationFixture} />);

    const table = screen.getByTestId('validation-fold-table');
    const body = table.querySelector('tbody');
    expect(body).not.toBeNull();
    const rows = within(body as HTMLElement).getAllByRole('row');
    expect(rows).toHaveLength(2);
    expect(within(rows[0]).getByText('F01')).toBeInTheDocument();
    expect(screen.getByText(/Leakage score: 0.040/)).toBeInTheDocument();
  });

  it('displays metadata and reported artifacts', () => {
    render(<ValidationOutputs validation={validationFixture} />);

    const metadata = screen.getByTestId('validation-metadata');
    expect(metadata).toHaveTextContent('leakage threshold');
    expect(metadata).toHaveTextContent('walk_forward_1');

    const artifactsTable = screen.getByTestId('validation-artifacts');
    expect(within(artifactsTable).getByText('validation/realism.json')).toBeInTheDocument();
    const artifactRows = within(artifactsTable).getAllByRole('row');
    expect(artifactRows.length).toBeGreaterThanOrEqual(3);
  });

  it('renders execution realism warnings, guidance, and assumptions', () => {
    render(<ValidationOutputs validation={validationFixture} />);

    expect(screen.getByTestId('validation-realism-warnings')).toHaveTextContent('Capacity ratio exceeds guidance band.');
    expect(screen.getByTestId('validation-realism-guidance')).toHaveTextContent('Maintain participation rate');
    expect(screen.getByTestId('validation-realism-assumptions')).toHaveTextContent('participation');
  });

  it('shows empty state when validation is absent', () => {
    render(<ValidationOutputs validation={undefined} />);
    expect(screen.getByTestId('validation-empty')).toBeInTheDocument();
  });
});
