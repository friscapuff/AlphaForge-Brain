/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Canonical validation payloads used across Mind tests.
 * Mirrors the contracts defined under `specs/010-description-integrate-masters/contracts/`.
 */

export type ValidationRunPayload = typeof validationRunPayload;
export type ValidationSseMessage = typeof validationSsePermutation;

export type DeepPartial<T> = {
  [K in keyof T]?: T[K] extends (infer R)[]
    ? DeepPartial<R>[]
    : T[K] extends object
      ? DeepPartial<T[K]>
      : T[K];
};

const baseRunId = "RUN-20251010-ABCD";

export const validationRunPayload = Object.freeze({
  run_id: baseRunId,
  validation: {
    schema_version: 2,
    significance_status: "pass",
    config: {
      modules: [
        "permutation",
        "dsr",
        "psr",
        "purged_kfold",
        "cpcv",
        "realism",
      ],
      permutation_count: 500,
      significance_threshold: 0.01,
      leakage_threshold: 0.1,
      realism_capacity_bps_limit: 500,
    },
    permutation: {
      segments: [
        {
          segment_id: "in_sample",
          p_value: 0.0042,
          effect_size: 1.8,
          executed_permutations: 500,
          requested_permutations: 500,
          histogram_summary: {
            mean: 0.41,
            std_dev: 0.12,
            percentiles: {
              5: 0.19,
              50: 0.4,
              95: 0.62,
            },
          },
          artifact_path: "validation/permutation/segment_in_sample.parquet",
        },
        {
          segment_id: "walk_forward_1",
          p_value: 0.0121,
          effect_size: 1.2,
          executed_permutations: 400,
          requested_permutations: 500,
          fallback_reason: "runtime_guard_triggered",
          histogram_summary: {
            mean: 0.35,
            std_dev: 0.15,
            percentiles: {
              5: 0.08,
              50: 0.33,
              95: 0.66,
            },
          },
          artifact_path: "validation/permutation/segment_walk_forward_1.parquet",
        },
      ],
    },
    bias_adjustments: {
      observed_sharpe: 1.95,
      deflated_sharpe: 1.62,
      probabilistic_sharpe: 0.987,
      assumed_trials: 120,
      benchmark_sharpe: 0.5,
      skewness: -0.3,
      kurtosis: 3.7,
      status: "pass",
    },
    cross_validation: {
      mode: "cpcv",
      leakage_score: 0.04,
      folds: [
        {
          fold_id: "F01",
          train: { start: "2018-01-01", end: "2019-12-31" },
          test: { start: "2020-01-01", end: "2020-03-31" },
          purge_span: "30D",
          metrics: {
            sharpe: 1.45,
            total_return: 0.12,
          },
        },
        {
          fold_id: "F02",
          train: { start: "2018-04-01", end: "2020-06-30" },
          test: { start: "2020-07-01", end: "2020-09-30" },
          purge_span: "30D",
          metrics: {
            sharpe: 1.51,
            total_return: 0.09,
          },
        },
      ],
    },
    execution_realism: {
      status: "pass",
      transaction_cost_bps: 35,
      market_impact_bps: 20,
      capacity_ratio: 0.72,
      warnings: [] as string[],
      assumptions: {
        adv_window_days: 30,
        participation_rate: 0.1,
        slippage_model: "square_root",
      },
    },
  },
} as const);

export const validationSsePermutation = Object.freeze({
  event: "validation.update",
  data: {
    run_id: baseRunId,
    correlation_id: "VAL-SEGMENT-in_sample",
    section: "permutation",
    payload: {
      segment_id: "in_sample",
      p_value: 0.0042,
      effect_size: 1.8,
      histogram_summary: {
        mean: 0.41,
        std_dev: 0.12,
        percentiles: {
          5: 0.19,
          50: 0.4,
          95: 0.62,
        },
      },
      artifact_path: "validation/permutation/segment_in_sample.parquet",
      executed_permutations: 500,
    },
  },
} as const);

function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}

function deepMerge(target: any, source: any): any {
  if (source === undefined) {
    return target;
  }
  if (Array.isArray(source)) {
    return source.slice();
  }
  if (source && typeof source === "object") {
    const result: Record<string, any> = { ...target };
    for (const [key, value] of Object.entries(source)) {
      result[key] = deepMerge((target as any)?.[key], value);
    }
    return result;
  }
  return source;
}

export function makeValidationRunPayload(
  overrides?: DeepPartial<ValidationRunPayload>,
): ValidationRunPayload {
  if (!overrides) {
    return deepClone(validationRunPayload);
  }
  return deepMerge(validationRunPayload, overrides) as ValidationRunPayload;
}

export function makeValidationSsePermutation(
  overrides?: DeepPartial<ValidationSseMessage>,
): ValidationSseMessage {
  if (!overrides) {
    return deepClone(validationSsePermutation);
  }
  return deepMerge(validationSsePermutation, overrides) as ValidationSseMessage;
}
