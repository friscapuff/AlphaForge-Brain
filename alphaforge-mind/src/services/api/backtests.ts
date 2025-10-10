import { apiClient } from './client.js';

// ----- API response shapes -----
export interface ApiValidationRunResponse {
  run_id: string;
  validation?: ApiValidationPayload | null;
}

export interface ApiValidationPayload {
  schema_version?: number;
  significance_status?: 'pass' | 'caution' | 'fail' | string | null;
  config?: ApiValidationConfig;
  modules?: Record<string, unknown> | null;
  failed_checks?: string[] | null;
  caution_checks?: string[] | null;
  metadata?: Record<string, unknown> | null;
  permutation?: ApiPermutationSection | null;
  bias_adjustments?: ApiBiasAdjustments | null;
  cross_validation?: ApiCrossValidation | null;
  execution_realism?: ApiExecutionRealism | null;
  manifest?: ApiValidationManifest | null;
  artifacts?: Record<string, ApiValidationArtifactMeta | null | undefined> | null;
  manifest_hash?: string | null;
}

export interface ApiValidationConfig {
  modules?: string[] | null;
  permutation_count?: number | null;
  significance_threshold?: number | null;
  leakage_threshold?: number | null;
  realism_capacity_bps_limit?: number | null;
  bias_absolute_threshold?: number | null;
  bias_relative_threshold?: number | null;
}

export interface ApiValidationManifestModule {
  enabled?: boolean | null;
  executed_permutations?: number | null;
}

export interface ApiValidationManifest {
  validation_schema_version?: number | null;
  validation_significance?: 'pass' | 'caution' | 'fail' | string | null;
  modules?: Record<string, ApiValidationManifestModule | null | undefined> | null;
  permutation_summary?: {
    segments?: Array<{
      segment_id?: string;
      executed_permutations?: number | null;
      requested_permutations?: number | null;
      effect_size?: number | null;
    }> | null;
  } | null;
  cross_validation?: Record<string, unknown> | null;
  execution_realism?: Record<string, unknown> | null;
  sharpe_adjustments?: Record<string, unknown> | null;
}

export interface ApiPermutationSection {
  segments?: ApiPermutationSegment[] | null;
}

export interface ApiPermutationSegment {
  segment_id: string;
  p_value?: number | null;
  effect_size?: number | null;
  executed_permutations?: number | null;
  requested_permutations?: number | null;
  observed_metric?: number | null;
  fallback_reason?: string | null;
  histogram_summary?: {
    mean?: number | null;
    std_dev?: number | null;
    percentiles?: Record<string, number> | null;
  } | null;
  artifact_path?: string | null;
}

export interface ApiValidationArtifactMeta {
  sha256?: string | null;
  size?: number | null;
}

export interface ApiBiasAdjustments {
  observed_sharpe?: number | null;
  deflated_sharpe?: number | null;
  probabilistic_sharpe?: number | null;
  assumed_trials?: number | null;
  benchmark_sharpe?: number | null;
  skewness?: number | null;
  kurtosis?: number | null;
  status?: 'pass' | 'caution' | 'fail';
}

export interface ApiCrossValidation {
  mode?: 'purged_kfold' | 'cpcv' | string | null;
  leakage_score?: number | null;
  bias_flag?: boolean | null;
  folds?: ApiCrossValidationFold[] | null;
}

export interface ApiCrossValidationFold {
  fold_id: string;
  train?: { start?: string | null; end?: string | null } | null;
  test?: { start?: string | null; end?: string | null } | null;
  purge_span?: string | null;
  metrics?: Record<string, number> | null;
}

export interface ApiExecutionRealism {
  status?: 'pass' | 'caution' | 'fail' | string | null;
  transaction_cost_bps?: number | null;
  market_impact_bps?: number | null;
  capacity_ratio?: number | null;
  warnings?: string[] | null;
  guidance?: string[] | null;
  assumptions?: Record<string, unknown> | null;
}

// ----- UI models -----
export type ValidationStatus = 'pass' | 'caution' | 'fail' | 'unknown';

export interface ValidationConfigModule {
  id: string;
  label: string;
  enabled: boolean;
}

export interface ValidationConfig {
  modules: ValidationConfigModule[];
  permutationCount?: number;
  significanceThreshold?: number;
  leakageThreshold?: number;
  realismCapacityBpsLimit?: number;
  biasAbsoluteThreshold?: number;
  biasRelativeThreshold?: number;
}

export interface PermutationHistogramSummary {
  mean?: number;
  stdDev?: number;
  percentiles: Array<{ percentile: number; value: number }>;
}

export interface PermutationSegment {
  segmentId: string;
  pValue?: number;
  effectSize?: number;
  observedMetric?: number;
  executedPermutations?: number;
  requestedPermutations?: number;
  fallbackReason?: string;
  histogramSummary?: PermutationHistogramSummary;
  artifactPath?: string;
}

export interface PermutationSection {
  segments: PermutationSegment[];
}

export interface BiasAdjustments {
  status: ValidationStatus;
  observedSharpe?: number;
  deflatedSharpe?: number;
  probabilisticSharpe?: number;
  assumedTrials?: number;
  benchmarkSharpe?: number;
  skewness?: number;
  kurtosis?: number;
}

export interface CrossValidationFold {
  foldId: string;
  trainRange?: { start?: string; end?: string };
  testRange?: { start?: string; end?: string };
  purgeSpan?: string;
  metrics: Record<string, number>;
}

export interface CrossValidationSection {
  mode?: string;
  leakageScore?: number;
  biasFlag?: boolean;
  folds: CrossValidationFold[];
}

export interface ExecutionRealismSection {
  status: ValidationStatus;
  transactionCostBps?: number;
  marketImpactBps?: number;
  capacityRatio?: number;
  warnings: string[];
  guidance: string[];
  assumptions: Record<string, unknown>;
}

export interface ValidationArtifact {
  path: string;
  sha256?: string;
  size?: number;
}

export interface ValidationData {
  schemaVersion?: number;
  significanceStatus: ValidationStatus;
  config: ValidationConfig;
  permutation?: PermutationSection;
  biasAdjustments?: BiasAdjustments;
  crossValidation?: CrossValidationSection;
  executionRealism?: ExecutionRealismSection;
  failedChecks: string[];
  cautionChecks: string[];
  metadata: Record<string, unknown>;
  manifestHash?: string;
  artifacts: ValidationArtifact[];
}

export interface BacktestRunData {
  runId: string;
  validation?: ValidationData;
}

// ----- Constants -----
const KNOWN_MODULES = ['permutation', 'dsr', 'psr', 'purged_kfold', 'cpcv', 'realism'] as const;
const MODULE_LABELS: Record<string, string> = {
  permutation: 'Permutation',
  dsr: 'Deflated Sharpe',
  psr: 'Probabilistic Sharpe',
  purged_kfold: 'Purged K-Fold',
  cpcv: 'CPCV',
  realism: 'Execution Realism',
};

// ----- Helpers -----
function toNumber(value: number | string | null | undefined): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return undefined;
}

function toPositiveNumber(value: number | string | null | undefined): number | undefined {
  const num = toNumber(value);
  return num !== undefined && !Number.isNaN(num) ? num : undefined;
}

function normalizePercentiles(record?: Record<string, number> | null): Array<{ percentile: number; value: number }> {
  if (!record) return [];
  return Object.entries(record)
    .map(([rawPercentile, rawValue]) => {
      const percentile = Number(rawPercentile);
      const value = Number(rawValue);
      if (Number.isFinite(percentile) && Number.isFinite(value)) {
        return { percentile, value };
      }
      return undefined;
    })
    .filter((entry): entry is { percentile: number; value: number } => Boolean(entry))
    .sort((a, b) => a.percentile - b.percentile);
}

function mapPermutationSegment(segment: ApiPermutationSegment): PermutationSegment {
  const histogram = segment.histogram_summary ?? undefined;
  return {
    segmentId: segment.segment_id,
    pValue: toPositiveNumber(segment.p_value ?? undefined),
    effectSize: toNumber(segment.effect_size ?? undefined),
    executedPermutations: toPositiveNumber(segment.executed_permutations ?? undefined),
    requestedPermutations: toPositiveNumber(segment.requested_permutations ?? undefined),
    observedMetric: toNumber(segment.observed_metric ?? undefined),
    fallbackReason: segment.fallback_reason ?? undefined,
    histogramSummary: histogram
      ? {
          mean: toNumber(histogram.mean ?? undefined),
          stdDev: toNumber(histogram.std_dev ?? undefined),
          percentiles: normalizePercentiles(histogram.percentiles ?? undefined),
        }
      : undefined,
    artifactPath: segment.artifact_path ?? undefined,
  };
}

function mapPermutationSection(section?: ApiPermutationSection | null): PermutationSection | undefined {
  if (!section?.segments?.length) return undefined;
  return {
    segments: section.segments.map(mapPermutationSegment),
  };
}

function mapBiasAdjustments(section?: ApiBiasAdjustments | null): BiasAdjustments | undefined {
  if (!section) return undefined;
  const status = section.status ?? (section.deflated_sharpe !== null && section.deflated_sharpe !== undefined ? 'pass' : 'unknown');
  return {
    status,
    observedSharpe: toNumber(section.observed_sharpe ?? undefined),
    deflatedSharpe: toNumber(section.deflated_sharpe ?? undefined),
    probabilisticSharpe: toNumber(section.probabilistic_sharpe ?? undefined),
    assumedTrials: toPositiveNumber(section.assumed_trials ?? undefined),
    benchmarkSharpe: toNumber(section.benchmark_sharpe ?? undefined),
    skewness: toNumber(section.skewness ?? undefined),
    kurtosis: toNumber(section.kurtosis ?? undefined),
  };
}

function normalizeRange(range?: { start?: string | null; end?: string | null } | null): { start?: string; end?: string } | undefined {
  if (!range) return undefined;
  const start = typeof range.start === 'string' ? range.start : undefined;
  const end = typeof range.end === 'string' ? range.end : undefined;
  if (start === undefined && end === undefined) return undefined;
  return { start, end };
}

function mapCrossValidation(section?: ApiCrossValidation | null, leakageThreshold?: number): CrossValidationSection | undefined {
  if (!section) return undefined;
  const folds = (section.folds ?? []).map((fold) => ({
    foldId: fold.fold_id,
    trainRange: normalizeRange(fold.train ?? undefined),
    testRange: normalizeRange(fold.test ?? undefined),
    purgeSpan: fold.purge_span ?? undefined,
    metrics: Object.fromEntries(
      Object.entries(fold.metrics ?? {}).filter(([, value]) => Number.isFinite(Number(value))).map(([key, value]) => [key, Number(value)])
    ),
  }));
  const leakageScore = toNumber(section.leakage_score ?? undefined);
  const explicitBiasFlag = typeof section.bias_flag === 'boolean' ? section.bias_flag : undefined;
  const derivedBiasFlag = typeof leakageThreshold === 'number' && typeof leakageScore === 'number'
    ? leakageScore > leakageThreshold
    : undefined;
  return {
    mode: section.mode ?? undefined,
    leakageScore,
    biasFlag: explicitBiasFlag ?? derivedBiasFlag ?? false,
    folds,
  };
}

function mapExecutionRealism(section?: ApiExecutionRealism | null): ExecutionRealismSection | undefined {
  if (!section) return undefined;
  const status = mapStatus(section.status ?? undefined);
  return {
    status,
    transactionCostBps: toNumber(section.transaction_cost_bps ?? undefined),
    marketImpactBps: toNumber(section.market_impact_bps ?? undefined),
    capacityRatio: toNumber(section.capacity_ratio ?? undefined),
    warnings: Array.isArray(section.warnings) ? section.warnings.filter((w): w is string => typeof w === 'string') : [],
    guidance: Array.isArray(section.guidance) ? section.guidance.filter((g): g is string => typeof g === 'string') : [],
    assumptions: section.assumptions ? { ...section.assumptions } : {},
  };
}

function extractModuleHints(modules?: Record<string, unknown> | null): string[] {
  if (!modules || typeof modules !== 'object') return [];
  const ids: string[] = [];
  for (const [key, value] of Object.entries(modules)) {
    if (!key) continue;
    if (typeof value === 'boolean') {
      if (value) ids.push(key);
      continue;
    }
    if (typeof value === 'string') {
      if (value.trim() !== '') ids.push(key);
      continue;
    }
    if (value !== null && value !== undefined) {
      ids.push(key);
    }
  }
  return ids;
}

function sanitizeStringList(values?: unknown): string[] {
  if (!Array.isArray(values)) return [];
  return values
    .map((value) => (typeof value === 'string' ? value.trim() : undefined))
    .filter((value): value is string => Boolean(value));
}

function cloneMetadataValue(value: unknown): unknown {
  if (value === null) return null;
  if (Array.isArray(value)) {
    return value
      .map((entry) => cloneMetadataValue(entry))
      .filter((entry) => entry !== undefined);
  }
  if (value && typeof value === 'object') {
    const entries: Record<string, unknown> = {};
    for (const [key, nested] of Object.entries(value as Record<string, unknown>)) {
      if (!key) continue;
      const cloned = cloneMetadataValue(nested);
      if (cloned !== undefined) {
        entries[key] = cloned;
      }
    }
    return entries;
  }
  if (typeof value === 'number' || typeof value === 'string' || typeof value === 'boolean') {
    return value;
  }
  return undefined;
}

function mapMetadata(metadata?: Record<string, unknown> | null): Record<string, unknown> {
  if (!metadata || typeof metadata !== 'object') return {};
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(metadata)) {
    if (!key) continue;
    const cloned = cloneMetadataValue(value);
    if (cloned !== undefined) {
      result[key] = cloned;
    }
  }
  return result;
}

function mapArtifacts(records?: Record<string, ApiValidationArtifactMeta | null | undefined> | null): ValidationArtifact[] {
  if (!records || typeof records !== 'object') return [];
  return Object.entries(records)
    .map(([path, meta]) => {
      if (typeof path !== 'string' || !path) return undefined;
      const sha256 = typeof meta?.sha256 === 'string' && meta.sha256.trim() ? meta.sha256.trim() : undefined;
      const size = toPositiveNumber(meta?.size ?? undefined);
      return { path, sha256, size } as ValidationArtifact;
    })
    .filter((entry): entry is ValidationArtifact => Boolean(entry))
    .sort((a, b) => a.path.localeCompare(b.path));
}

function mapValidationModules(
  manifestModules?: Record<string, ApiValidationManifestModule | null | undefined> | null,
  configModules?: string[] | null,
  hints?: string[] | null,
): ValidationConfigModule[] {
  const manifest = manifestModules ?? {};
  const configSet = new Set(
    Array.isArray(configModules) ? configModules.filter((id): id is string => typeof id === 'string') : [],
  );
  if (Array.isArray(hints)) {
    for (const hint of hints) {
      if (typeof hint === 'string' && hint) {
        configSet.add(hint);
      }
    }
  }
  const knownModules = KNOWN_MODULES.map((id) => {
    const manifestEntry = manifest[id];
    const enabled = typeof manifestEntry?.enabled === 'boolean' ? manifestEntry.enabled : configSet.has(id);
    return {
      id,
      label: MODULE_LABELS[id] ?? id,
      enabled,
    } satisfies ValidationConfigModule;
  });
  const extraModules: ValidationConfigModule[] = [];
  for (const [id, entry] of Object.entries(manifest)) {
    if (KNOWN_MODULES.includes(id as typeof KNOWN_MODULES[number])) continue;
    const enabled = typeof entry?.enabled === 'boolean' ? entry.enabled : configSet.has(id);
    extraModules.push({
      id,
      label: id.replace(/_/g, ' '),
      enabled: Boolean(enabled),
    });
  }
  for (const id of configSet) {
    if (KNOWN_MODULES.includes(id as typeof KNOWN_MODULES[number])) continue;
    if (extraModules.some((module) => module.id === id)) continue;
    extraModules.push({
      id,
      label: id.replace(/_/g, ' '),
      enabled: true,
    });
  }
  return [...knownModules, ...extraModules];
}

function mapConfig(
  config?: ApiValidationConfig | null,
  manifest?: ApiValidationManifest | null,
  moduleHints?: string[] | null,
): ValidationConfig {
  return {
    modules: mapValidationModules(manifest?.modules ?? undefined, config?.modules ?? undefined, moduleHints),
    permutationCount: toPositiveNumber(config?.permutation_count ?? undefined),
    significanceThreshold: toNumber(config?.significance_threshold ?? undefined),
    leakageThreshold: toNumber(config?.leakage_threshold ?? undefined),
    realismCapacityBpsLimit: toNumber(config?.realism_capacity_bps_limit ?? undefined),
    biasAbsoluteThreshold: toNumber(config?.bias_absolute_threshold ?? undefined),
    biasRelativeThreshold: toNumber(config?.bias_relative_threshold ?? undefined),
  };
}

function mapStatus(status?: string | null): ValidationStatus {
  if (status === 'pass' || status === 'caution' || status === 'fail') {
    return status;
  }
  return 'unknown';
}

export function mapBacktestValidation(payload?: ApiValidationPayload | null): ValidationData | undefined {
  if (!payload) return undefined;
  const manifest = payload.manifest ?? undefined;
  const moduleHints = extractModuleHints(payload.modules ?? undefined);
  const config = mapConfig(payload.config ?? undefined, manifest ?? undefined, moduleHints);
  const metadata = mapMetadata(payload.metadata ?? undefined);
  const leakageThreshold =
    config.leakageThreshold ?? toNumber((metadata?.leakage_threshold as number | string | undefined) ?? undefined);
  const manifestHash =
    typeof payload.manifest_hash === 'string' && payload.manifest_hash.trim()
      ? payload.manifest_hash.trim()
      : undefined;
  return {
    schemaVersion: typeof payload.schema_version === 'number' ? payload.schema_version : undefined,
    significanceStatus: mapStatus(payload.significance_status ?? undefined),
    config,
    permutation: mapPermutationSection(payload.permutation ?? undefined),
    biasAdjustments: mapBiasAdjustments(payload.bias_adjustments ?? undefined),
    crossValidation: mapCrossValidation(payload.cross_validation ?? undefined, leakageThreshold),
    executionRealism: mapExecutionRealism(payload.execution_realism ?? undefined),
    failedChecks: sanitizeStringList(payload.failed_checks ?? undefined),
    cautionChecks: sanitizeStringList(payload.caution_checks ?? undefined),
    metadata,
    manifestHash,
    artifacts: mapArtifacts(payload.artifacts ?? undefined),
  };
}

export function deriveValidationCaution(validation?: ValidationData): { caution: boolean; metrics: string[] } {
  if (!validation) return { caution: false, metrics: [] };
  const metrics = new Set<string>();
  validation.failedChecks.forEach((check) => metrics.add(`failed.${check}`));
  validation.cautionChecks.forEach((check) => metrics.add(`caution.${check}`));
  if (validation.significanceStatus === 'caution' || validation.significanceStatus === 'fail') {
    metrics.add('validation.significance');
  }
  const threshold = validation.config.significanceThreshold;
  const segments = validation.permutation?.segments ?? [];
  if (typeof threshold === 'number' && segments.length > 0) {
    segments.forEach((segment) => {
      if (segment.pValue !== undefined && segment.pValue > threshold) {
        metrics.add(`permutation.${segment.segmentId}`);
      }
    });
  }
  const cv = validation.crossValidation;
  if (cv?.biasFlag) {
    metrics.add('cross_validation.bias');
  }
  if (typeof cv?.leakageScore === 'number' && typeof validation.config.leakageThreshold === 'number') {
    if (cv.leakageScore > validation.config.leakageThreshold) {
      metrics.add('cross_validation.leakage');
    }
  }
  const realism = validation.executionRealism;
  if (realism) {
    if (realism.status === 'caution' || realism.status === 'fail') {
      metrics.add('execution_realism.status');
    }
    if (realism.warnings.length > 0) {
      metrics.add('execution_realism.warnings');
    }
  }
  const bias = validation.biasAdjustments;
  if (bias?.status === 'caution' || bias?.status === 'fail') {
    metrics.add('bias_adjustments.status');
  }
  const metadata = validation.metadata;
  const permutationShortfalls = metadata['permutation_shortfalls'];
  if (Array.isArray(permutationShortfalls) && permutationShortfalls.length > 0) {
    metrics.add('permutation.shortfalls');
  }
  const permutationFallbacks = metadata['permutation_fallbacks'];
  if (Array.isArray(permutationFallbacks) && permutationFallbacks.length > 0) {
    metrics.add('permutation.fallbacks');
  }
  if (metadata['cross_validation_bias_flag'] === true) {
    metrics.add('cross_validation.bias');
  }
  const realismStatusValue = metadata['realism_status'];
  const realismStatus = typeof realismStatusValue === 'string' ? realismStatusValue : undefined;
  if (realismStatus === 'caution' || realismStatus === 'fail') {
    metrics.add('execution_realism.status');
  }
  return { caution: metrics.size > 0, metrics: Array.from(metrics) };
}

export async function fetchBacktestValidation(runId: string): Promise<BacktestRunData> {
  const response = await apiClient.json<ApiValidationRunResponse>(`/runs/${runId}`);
  return {
    runId: response.run_id,
    validation: mapBacktestValidation(response.validation ?? undefined),
  };
}
