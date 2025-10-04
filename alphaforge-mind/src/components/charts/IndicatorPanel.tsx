import React from 'react';
import { IndicatorManager, type IndicatorManagerRenderProps } from './IndicatorManager.js';
import { CandleChart, type CandleDataPoint } from './CandleChart.js';

/**
 * IndicatorPanel (T033)
 * Composes CandleChart + Indicator management UI scaffolding.
 * For now, only renders the CandleChart and a minimal list of active indicators with controls.
 * Future: parameter editing forms, color pickers, draggable ordering, persistence.
 */

export interface IndicatorPanelProps {
  candles: CandleDataPoint[];
  className?: string;
}

export function IndicatorPanel({ candles, className }: IndicatorPanelProps): React.ReactElement {
  return React.createElement(
    'div',
    { className, style: { display: 'flex', flexDirection: 'column', gap: 12 } as React.CSSProperties },
    React.createElement(
      IndicatorManager,
      { initial: [], children: (props: IndicatorManagerRenderProps) => {
        const { indicators, addIndicator, removeIndicator, toggleIndicator } = props;
        return React.createElement(
          React.Fragment,
          null,
          React.createElement(
            'div',
            { style: { display: 'flex', gap: 8, alignItems: 'center' } as React.CSSProperties },
            React.createElement(
              'button',
              {
                type: 'button',
                onClick: () => addIndicator('sma', { length: 20 }),
                className: 'px-2 py-1 rounded bg-neutral-800 border border-neutral-700 text-xs',
              },
              '+ SMA(20)'
            ),
            React.createElement(
              'button',
              {
                type: 'button',
                onClick: () => addIndicator('ema', { length: 50 }),
                className: 'px-2 py-1 rounded bg-neutral-800 border border-neutral-700 text-xs',
              },
              '+ EMA(50)'
            ),
            React.createElement(
              'div',
              { className: 'text-xs text-neutral-500' },
              `Indicators: ${indicators.length}`
            )
          ),
          React.createElement(CandleChart, { data: candles, height: 360 }),
          indicators.length > 0
            ? React.createElement(
                'div',
                { className: 'mt-2 border border-neutral-800 rounded p-2 bg-neutral-900/50' },
                React.createElement(
                  'div',
                  { className: 'text-xs font-semibold mb-1 text-neutral-400' },
                  'Active Indicators'
                ),
                React.createElement(
                  'ul',
                  { className: 'space-y-1' },
                  indicators.map(ind =>
                    React.createElement(
                      'li',
                      { key: ind.id, className: 'flex items-center gap-2 text-xs' },
                      React.createElement(
                        'button',
                        {
                          type: 'button',
                          onClick: () => toggleIndicator(ind.id),
                          className: 'px-1 py-0.5 rounded border border-neutral-700 bg-neutral-800',
                        },
                        ind.enabled ? '⏸' : '▶'
                      ),
                      React.createElement(
                        'span',
                        { className: ind.enabled ? 'text-neutral-200' : 'text-neutral-500 line-through' },
                        `${ind.type.toUpperCase()} ${JSON.stringify(ind.params)}`
                      ),
                      React.createElement(
                        'button',
                        {
                          type: 'button',
                          onClick: () => removeIndicator(ind.id),
                          className: 'ml-auto px-1 py-0.5 rounded border border-neutral-700 bg-neutral-800 text-red-300',
                        },
                        '✕'
                      )
                    )
                  )
                )
              )
            : null
        );
      } }
    )
  );
}

export default IndicatorPanel;
