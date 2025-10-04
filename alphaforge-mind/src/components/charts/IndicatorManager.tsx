import React from 'react';

/**
 * IndicatorManager (T031)
 * Skeleton component responsible for:
 *  - Managing a list/registry of active technical indicators for the current chart symbol+interval
 *  - Handling add/remove/toggle operations (will integrate with Zustand slices in later tasks)
 *  - Providing a render prop / children function with the resolved indicator data & metadata
 *
 * This is an initial stub to unblock T032/T033. Implementation details (state wiring, forms,
 * persistence, parameter editing) will be filled in subsequent tasks.
 */

export interface IndicatorDefinition {
  id: string;              // unique internal id (e.g., uuid or `${type}-${n}`)
  type: string;            // indicator type key, e.g. 'sma', 'ema', 'rsi'
  params: Record<string, unknown>; // parameter map (length, period, etc.)
  color?: string;          // preferred line/color styling hint
  enabled: boolean;        // quick toggle
}

export interface IndicatorManagerRenderProps {
  indicators: IndicatorDefinition[];
  addIndicator: (type: string, params?: Record<string, unknown>) => void;
  removeIndicator: (id: string) => void;
  toggleIndicator: (id: string) => void;
  updateParams: (id: string, params: Record<string, unknown>) => void;
}

export interface IndicatorManagerProps {
  /** Optional initial seed list of indicators */
  initial?: IndicatorDefinition[];
  /** Children render pattern for composition */
  children: (renderProps: IndicatorManagerRenderProps) => React.ReactNode;
}

export function IndicatorManager({ initial = [], children }: IndicatorManagerProps): React.ReactElement {
  const [indicators, setIndicators] = React.useState<IndicatorDefinition[]>(() => initial);

  const addIndicator = React.useCallback((type: string, params: Record<string, unknown> = {}) => {
    setIndicators(prev => [
      ...prev,
      {
        id: `${type}-${prev.length + 1}`,
        type,
        params,
        enabled: true,
      },
    ]);
  }, []);

  const removeIndicator = React.useCallback((id: string) => {
    setIndicators(prev => prev.filter(i => i.id !== id));
  }, []);

  const toggleIndicator = React.useCallback((id: string) => {
    setIndicators(prev => prev.map(i => (i.id === id ? { ...i, enabled: !i.enabled } : i)));
  }, []);

  const updateParams = React.useCallback((id: string, params: Record<string, unknown>) => {
    setIndicators(prev => prev.map(i => (i.id === id ? { ...i, params: { ...i.params, ...params } } : i)));
  }, []);

  return React.createElement(
    React.Fragment,
    null,
    children({ indicators, addIndicator, removeIndicator, toggleIndicator, updateParams })
  );
}

export default IndicatorManager;
