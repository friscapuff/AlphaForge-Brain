/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Canonical trust gate payloads used across Mind tests.
 * Mirrors the contracts under `specs/011-trust-gate-framework/contracts/`.
 */

import type { DeepPartial } from "./validationPayload.js";

export type TrustGateRunPayload = typeof trustGateRunPayload;
export type TrustGateSseUpdate = typeof trustGateSseUpdate;

const baseRunId = "run_20251011_abcdef01";
const correlationBase = "tg-20251011";

export const trustGateRunPayload = Object.freeze({
  id: baseRunId,
  status: "ready",
  trust_gate: {
    schema_version: "trust_gates.v1",
    executed_at: "2025-10-11T14:22:45.137Z",
    suite_version: 1,
    config_hash: "sha256:e602e007b8456d416ad0285dbf289be15328c0f431971826d5bea01e6e7d7e8b",
    tolerance_profile: "institutional_default",
    runtime_ms: 68432,
    status: "pass",
    gates: [
      {
        name: "golden_run",
        status: "pass",
        duration_ms: 8421,
        tolerance: { hash_equal: true },
        artifact:
          "artifacts/trust_gates/reports/golden_run_v1/gate_golden_run_diagnostics.json",
        correlation_id: `${correlationBase}-0001`,
      },
      {
        name: "causality",
        status: "pass",
        duration_ms: 10952,
        metrics: { leakage_score: 0.0028, equity_drift: 0.0 },
        artifact:
          "artifacts/trust_gates/reports/golden_run_v1/gate_causality_diagnostics.json",
        correlation_id: `${correlationBase}-0002`,
      },
      {
        name: "ingest_idempotency",
        status: "pass",
        duration_ms: 18765,
        metrics: { dataset_hash_match: true, vendor_retries: 1 },
        tolerance: { max_retries: 3 },
        artifact:
          "artifacts/trust_gates/reports/golden_run_v1/ingest_vendor_metadata.json",
        correlation_id: `${correlationBase}-0003`,
      },
      {
        name: "timezone",
        status: "pass",
        duration_ms: 6250,
        metrics: { dst_anomalies: 0, leap_seconds_detected: 0 },
        artifact:
          "artifacts/trust_gates/reports/golden_run_v1/gate_timezone_diagnostics.json",
        correlation_id: `${correlationBase}-0004`,
      },
      {
        name: "universe_stamp",
        status: "pass",
        duration_ms: 4731,
        metrics: { missing_symbols: [] as string[] },
        artifact:
          "artifacts/trust_gates/reports/golden_run_v1/gate_universe_stamp_diagnostics.json",
        correlation_id: `${correlationBase}-0005`,
      },
      {
        name: "equity_reconciliation",
        status: "pass",
        duration_ms: 9522,
        metrics: { max_basis_point_drift: 2.1, max_currency_delta: 0.0032 },
        artifact:
          "artifacts/trust_gates/reports/golden_run_v1/gate_equity_reconciliation.json",
        correlation_id: `${correlationBase}-0006`,
      },
      {
        name: "accounting",
        status: "pass",
        duration_ms: 10188,
        metrics: { max_currency_delta: 0.0026, unmatched_trade_ids: [] as string[] },
        artifact:
          "artifacts/trust_gates/reports/golden_run_v1/gate_accounting_diagnostics.json",
        correlation_id: `${correlationBase}-0007`,
      },
    ],
    signature_path:
      "artifacts/trust_gates/reports/golden_run_v1/trust_gate_report.sig",
  },
} as const);

export const trustGateSseUpdate = Object.freeze({
  event: "run.update",
  data: {
    run_id: baseRunId,
    section: "trust_gate",
    payload: {
      status: "fail",
      executed_at: "2025-10-11T14:25:03.511Z",
      failed_gates: [
        {
          name: "timezone",
          status: "fail" as const,
          message:
            "Ambiguous DST transition detected for symbol AAPL on 2014-03-09",
          correlation_id: `${correlationBase}-0005`,
        },
      ],
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

export function makeTrustGateRunPayload(
  overrides?: DeepPartial<TrustGateRunPayload>,
): TrustGateRunPayload {
  if (!overrides) {
    return deepClone(trustGateRunPayload);
  }
  return deepMerge(trustGateRunPayload, overrides) as TrustGateRunPayload;
}

export function makeTrustGateSseUpdate(
  overrides?: DeepPartial<TrustGateSseUpdate>,
): TrustGateSseUpdate {
  if (!overrides) {
    return deepClone(trustGateSseUpdate);
  }
  return deepMerge(trustGateSseUpdate, overrides) as TrustGateSseUpdate;
}
