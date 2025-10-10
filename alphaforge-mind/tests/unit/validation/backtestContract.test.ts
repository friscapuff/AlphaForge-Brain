import { describe, it, expect } from 'vitest';
import {
  mapBacktestValidation,
  deriveValidationCaution,
  type ApiValidationPayload,
} from '../../../src/services/api/backtests.js';

describe('mapBacktestValidation', () => {
  const payload: ApiValidationPayload = {
    schema_version: 2,
    significance_status: 'caution',
    config: {
      modules: ['permutation', 'dsr'],
      significance_threshold: 0.01,
      leakage_threshold: 0.1,
      bias_absolute_threshold: 0.25,
      bias_relative_threshold: 0.6,
    },
    modules: {
      permutation: true,
      cross_validation: 'cpcv',
      execution_realism: true,
    },
    failed_checks: ['cross_validation'],
    caution_checks: ['permutation_sampling'],
    metadata: {
      leakage_threshold: 0.1,
      permutation_shortfalls: [{ segment_id: 'walk_forward', requested: 500, executed: 420 }],
      realism_status: 'caution',
    },
    permutation: {
      segments: [
        {
          segment_id: 'walk_forward',
          p_value: 0.02,
          effect_size: 1.2,
          observed_metric: 0.95,
          executed_permutations: 420,
          requested_permutations: 500,
        },
      ],
    },
    bias_adjustments: {
      status: 'pass',
      observed_sharpe: 1.5,
      deflated_sharpe: 1.3,
    },
    cross_validation: {
      mode: 'cpcv',
      leakage_score: 0.15,
      bias_flag: true,
      folds: [],
    },
    execution_realism: {
      status: 'caution',
      warnings: ['capacity warning'],
      guidance: ['reduce participation'],
      assumptions: { participation: '0.08' },
    },
    manifest: {
      validation_schema_version: 2,
      modules: {
        permutation: { enabled: true, executed_permutations: 420 },
        dsr: { enabled: true },
        psr: { enabled: false },
        purged_kfold: { enabled: false },
        cpcv: { enabled: true },
        realism: { enabled: true },
      },
    },
    artifacts: {
      'validation/permutation/segment_walk_forward.parquet': {
        size: 1024,
        sha256: 'abc123def456',
      },
      'validation/realism.json': {
        size: 2048,
        sha256: 'ffeeddccbbaa',
      },
    },
    manifest_hash: 'f00dface0123456789abcdef0123456789abcdef0123456789abcdef01234567',
  };

  it('normalizes modules, metadata, and artifacts from API payload', () => {
    const mapped = mapBacktestValidation(payload);
    expect(mapped).toBeDefined();
    expect(mapped?.manifestHash).toBe(payload.manifest_hash);
    expect(mapped?.metadata['leakage_threshold']).toBe(0.1);
    expect(Array.isArray(mapped?.metadata['permutation_shortfalls'])).toBe(true);
    const modules = mapped?.config.modules ?? [];
    expect(modules.find((mod) => mod.id === 'permutation')?.enabled).toBe(true);
    expect(modules.find((mod) => mod.id === 'psr')?.enabled).toBe(false);
    expect(mapped?.artifacts.map((artifact) => artifact.path)).toEqual([
      'validation/permutation/segment_walk_forward.parquet',
      'validation/realism.json',
    ]);
  });

  it('propagates gating checks into caution metrics', () => {
    const mapped = mapBacktestValidation(payload);
    const caution = deriveValidationCaution(mapped);
    expect(caution.caution).toBe(true);
    expect(caution.metrics).toContain('failed.cross_validation');
    expect(caution.metrics).toContain('caution.permutation_sampling');
    expect(caution.metrics).toContain('permutation.shortfalls');
    expect(caution.metrics).toContain('execution_realism.status');
  });
});
