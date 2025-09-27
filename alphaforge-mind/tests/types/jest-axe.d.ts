// Minimal ambient types for jest-axe to satisfy TS in vitest context
// We only use axe() and toHaveNoViolations matcher.

declare module 'jest-axe' {
  export interface AxeNodeResult {
    target: string[];
    html: string;
    failureSummary?: string;
  }
  export interface AxeViolation {
    id: string;
    impact?: string; // 'minor' | 'moderate' | 'serious' | 'critical'
    description: string;
    help: string;
    helpUrl: string;
    tags: string[];
    nodes: AxeNodeResult[];
  }
  export interface AxeResults {
    violations: AxeViolation[];
    passes: AxeViolation[];
    incomplete: AxeViolation[];
    inapplicable: AxeViolation[];
  }
  export function axe(container: HTMLElement, options?: unknown): Promise<AxeResults>;
  export function toHaveNoViolations(results: AxeResults): void;
}

declare global {
  // Vitest merges jest matchers, extend signature loosely
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace jest {
    interface Matchers<R> {
      toHaveNoViolations(): R;
    }
  }
}

export {};
