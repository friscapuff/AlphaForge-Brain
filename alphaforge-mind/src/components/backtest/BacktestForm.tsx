import React from 'react';
import { validateBacktestInput, canonicalizeBacktestInput, type BacktestFormInput } from '../../utils/validation.js';

export interface BacktestFormProps {
  onSubmit: (data: BacktestFormInput & { equity: number }) => void;
}

export function BacktestForm({ onSubmit }: BacktestFormProps): React.ReactElement {
  const [errors, setErrors] = React.useState<string[]>([]);
  const handle = (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement & { elements: any };
    const data: BacktestFormInput = {
      start: (form.elements.namedItem('start') as HTMLInputElement).value,
      end: (form.elements.namedItem('end') as HTMLInputElement).value,
      strategy: (form.elements.namedItem('strategy') as HTMLInputElement).value,
      equity: (form.elements.namedItem('equity') as HTMLInputElement).value,
    };
    const result = validateBacktestInput(data);
    if (!result.ok) {
      setErrors(result.issues.map(i => i.message));
      return;
    }
    setErrors([]);
    onSubmit(canonicalizeBacktestInput(data));
  };

  return React.createElement(
    'form',
    { onSubmit: handle, 'data-testid': 'backtest-form' },
    React.createElement('input', { name: 'start', placeholder: 'start' }),
    React.createElement('input', { name: 'end', placeholder: 'end' }),
    React.createElement('input', { name: 'strategy', placeholder: 'strategy name' }),
    React.createElement('input', { name: 'equity', placeholder: 'initial equity' }),
    React.createElement('button', { type: 'submit' }, 'run-backtest'),
    React.createElement(
      'ul',
      { 'data-testid': 'errors' },
      errors.map(e => React.createElement('li', { key: e }, e))
    )
  );
}

export default BacktestForm;
