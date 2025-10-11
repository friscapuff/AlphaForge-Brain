import { apiClient } from '../api/client.js';

export interface PromSample {
  metric: string;
  labels: Record<string, string>;
  value: number;
}

export interface TrustGateGateMetrics {
  name: string;
  statusValue: number;
  healthy: boolean;
  failureCount: number;
  meanDurationMs?: number;
}

export interface TrustGateMetrics {
  collectedAt: Date;
  gates: TrustGateGateMetrics[];
  raw: string;
}

const PROM_LINE = /^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]+\})?\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?|[+-]?Inf|NaN)$/;
const LABEL_RE = /([^=",\s]+)="((?:\\"|[^"\\])*)"/g;

function resolveMetricsUrl(): string {
  const envUrl = (import.meta as any)?.env?.VITE_PROM_METRICS_URL;
  if (typeof envUrl === 'string' && envUrl.trim().length > 0) {
    return envUrl.trim();
  }
  try {
    const url = new URL(apiClient.baseUrl);
    const replaced = url.pathname.replace(/\/?api\/?v1\/?$/, '/metrics');
    url.pathname = replaced.endsWith('/metrics') ? replaced : `${replaced.replace(/\/$/, '')}/metrics`;
    url.search = '';
    return url.toString();
  } catch {
    return '/metrics';
  }
}

function parseLabels(input?: string): Record<string, string> {
  if (!input) return {};
  const labels: Record<string, string> = {};
  const body = input.slice(1, -1);
  const regex = new RegExp(LABEL_RE);
  let match: RegExpExecArray | null;
  while ((match = regex.exec(body)) !== null) {
    const key = match[1];
    const raw = match[2];
    labels[key] = raw.replace(/\\"/g, '"').replace(/\\\\/g, '\\');
  }
  return labels;
}

function parsePrometheus(text: string): PromSample[] {
  const samples: PromSample[] = [];
  const lines = text.split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const match = trimmed.match(PROM_LINE);
    if (!match) continue;
    const [, metric, labelBlock, valueRaw] = match;
    const value = parseFloat(valueRaw);
    if (!Number.isFinite(value) && valueRaw !== 'NaN') continue;
    samples.push({ metric, labels: parseLabels(labelBlock), value });
  }
  return samples;
}

function coalesceMetricValue(samples: PromSample[], metric: string, labels: Record<string, string>): number | undefined {
  const found = samples.find((sample) => {
    if (sample.metric !== metric) return false;
    return Object.entries(labels).every(([key, val]) => sample.labels[key] === val);
  });
  return found?.value;
}

function summarizeGates(samples: PromSample[]): TrustGateGateMetrics[] {
  const gates = new Map<string, TrustGateGateMetrics>();
  for (const sample of samples) {
    const gate = sample.labels['gate'];
    if (!gate) continue;
    if (!gates.has(gate)) {
      gates.set(gate, {
        name: gate,
        statusValue: 1,
        healthy: true,
        failureCount: 0,
      });
    }
    const entry = gates.get(gate)!;
    if (sample.metric === 'trust_gate_status') {
      entry.statusValue = sample.value;
      entry.healthy = sample.value >= 0.5;
    } else if (sample.metric === 'trust_gate_failures_total') {
      entry.failureCount = sample.value;
    } else if (sample.metric === 'trust_gate_duration_seconds_sum') {
      const count = coalesceMetricValue(samples, 'trust_gate_duration_seconds_count', { gate });
      if (count && count > 0) {
        entry.meanDurationMs = (sample.value / count) * 1000;
      }
    }
  }
  return Array.from(gates.values()).sort((a, b) => a.name.localeCompare(b.name));
}

export async function fetchTrustGateMetrics(): Promise<TrustGateMetrics> {
  const metricsUrl = resolveMetricsUrl();
  const resp = await fetch(metricsUrl, { headers: { Accept: 'text/plain' } });
  if (!resp.ok) {
    throw new Error(`Prometheus query failed with status ${resp.status}`);
  }
  const body = await resp.text();
  const samples = parsePrometheus(body);
  const gates = summarizeGates(samples);
  return {
    collectedAt: new Date(),
    gates,
    raw: body,
  };
}

export type { PromSample as TrustGatePromSample };
export { parsePrometheus };
