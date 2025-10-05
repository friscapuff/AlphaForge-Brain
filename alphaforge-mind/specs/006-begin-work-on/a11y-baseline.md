# Accessibility Baseline (T052)

Initial measures introduced:

- Skip link for keyboard users to jump to main content.
- Landmark role `main` with aria-label.
- Section headings associated via `aria-labelledby` (configuration, runs, results, feature flags).
- ErrorBoundary alert region uses `role="alert"` (inherent announcement for errors).
- Buttons have visible text; placeholder toggle components remain accessible as they are simple buttons/checkboxes.

Deferred / Future (not in T052 scope):
- Color contrast audit with design tokens.
- Focus outlines theming and trap management for modals.
- ARIA descriptions for complex charts (Monte Carlo canvas, equity curve) and potential `aria-live` region for run status updates.
- Playwright + Axe automated scan tasks (T092, T093) to follow.

This document will evolve as additional A11Y tasks (T092, T093) are completed.
