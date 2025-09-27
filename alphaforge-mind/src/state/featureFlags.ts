/**
 * featureFlags.ts (T051 early)
 * Minimal feature flag scaffolding introduced early to avoid retrofitting.
 */
import { create } from 'zustand';

export interface FeatureFlagsState {
  extendedPercentiles: boolean;
  advancedValidation: boolean;
  setFlag: (k: keyof Omit<FeatureFlagsState, 'setFlag'>, v: boolean) => void;
}

export const useFeatureFlags = create<FeatureFlagsState>()(() => ({
  extendedPercentiles: false,
  advancedValidation: false,
  setFlag(k, v) { (this as any)[k] = v; },
}));
