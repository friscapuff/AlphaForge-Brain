import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchTrustGateMetrics, parsePrometheus } from '../../../src/services/metrics/trustGates.js';

describe('trust gate Prometheus parser', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('parses trust gate samples with labels', () => {
    const body = `# HELP trust_gate_status Gauge of pass/fail\ntrust_gate_status{gate="golden_run"} 1\ntrust_gate_status{gate="timezone",env="prod"} 0\n`;
    const samples = parsePrometheus(body);
    expect(samples).toHaveLength(2);
    const timezone = samples.find((s) => s.labels.gate === 'timezone');
    expect(timezone?.metric).toBe('trust_gate_status');
    expect(timezone?.labels.env).toBe('prod');
    expect(timezone?.value).toBe(0);
  });

  it('summarises gate health and duration', async () => {
    const payload = `# TYPE trust_gate_status gauge\ntrust_gate_status{gate="golden_run"} 1\ntrust_gate_status{gate="timezone"} 0\ntrust_gate_failures_total{gate="timezone"} 3\ntrust_gate_duration_seconds_sum{gate="timezone"} 12\ntrust_gate_duration_seconds_count{gate="timezone"} 3\n`;

    const fetchMock = vi.spyOn(global, 'fetch').mockResolvedValue(
      new Response(payload, { status: 200, headers: { 'Content-Type': 'text/plain' } })
    );

    const metrics = await fetchTrustGateMetrics();
    expect(fetchMock).toHaveBeenCalled();
    expect(metrics.gates).toHaveLength(2);

    const timezone = metrics.gates.find((gate) => gate.name === 'timezone');
    expect(timezone).toBeDefined();
    expect(timezone?.healthy).toBe(false);
    expect(timezone?.failureCount).toBe(3);
    expect(timezone?.meanDurationMs).toBeCloseTo(4000);
  });
});
