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
