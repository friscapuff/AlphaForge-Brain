# AlphaForge Mind

Deterministic frontend (React + TypeScript) consuming AlphaForge Brain APIs to deliver:

1. Chart Analysis Tab (FR-001..FR-002, FR-016): Candles, indicators, timeframe switching.
2. Backtest & Validation Tab (FR-003..FR-010, FR-013..FR-015, FR-018–FR-022): Strategy config, run orchestration, metrics & validation visualization, Monte Carlo overlays.

## Principles (Constitution Mapping)
- Determinism (DET): No client-side randomization; all stochastic outputs (Monte Carlo, permutations) sourced from Brain with seed.
- Test-First (TF): Contract, unit, and integration tests precede implementation (Vitest + Testing Library).
- Modularity (MOD): Feature slices under `src/` (charts/, backtest/, state/, services/).
- Observability (OBS): API client timing logs & status polling instrumentation.
- Performance (PERF): Lightweight-charts, memoized selectors, batch Monte Carlo drawing.

## Structure
```
alphaforge-mind/
	src/
		components/
		pages/
		hooks/
		services/
		state/
		styles/
	tests/
		unit/
		integration/
		contracts/
```

## Getting Started (Early Scaffold)
```
pnpm install  # or npm install / yarn
pnpm dev      # Vite dev server (will integrate routes incrementally)
```

### Masters Validation Surface
- **Environment toggles**: ensure the Brain process exports the validation modules env vars documented in the root README/quickstart so SSE payloads include permutation, bias, CPCV, and realism sections.
- **Data adapters**: `src/services/api/backtests.ts` normalizes `validation.permutation`, `validation.bias_adjustments`, `validation.cross_validation`, and `validation.execution_realism` fields; keep schema changes additive.
- **UI components**: `src/components/validation/` hosts charts/cards for each module. The Validation tab reads toggle state from `validation_config` and renders caution badges + remediation copy sourced from API payloads.
- **Smoke checks**: run `npm test` (Vitest) plus `poetry run pytest alphaforge-brain/tests/property/validation/test_permutation_distribution.py --no-cov` to confirm both Mind adapters and Brain histograms remain in sync before releasing UI tweaks.

## Pending Setup Tasks (T001–T005)
- [x] T001 Dual root scaffold & README stub
- [x] T002 Dependencies validation / additions
- [x] T003 ESLint + Prettier config
- [x] T004 Vitest config & setup file
- [x] T005 .env.example with `VITE_API_BASE_URL`

## Do / Don't
Do: Access Brain only via HTTP contracts (no direct Python imports).
Don't: Introduce global mutable singletons beyond the small Zustand store.

---
Incrementally expanded as tasks progress.
