# AlphaForge Mind Quickstart (Feature 006)

This quickstart guides initial setup for the React + Tailwind + lightweight-charts (LWC) frontend (AlphaForge Mind) to deliver Chart Analysis and Backtest/Validation tabs.

## Prerequisites
- Node.js 20.x
- PNPM or NPM (prefer PNPM for workspace speed) — choose one and remain consistent
- Python 3.11 runtime (Brain backend) accessible locally for contract dev
- Git feature branch: `006-begin-work-on`

## Directory Bootstrapping (Planned)
```
alphaforge-mind/
  package.json
  tailwind.config.cjs
  postcss.config.cjs
  src/
    main.tsx
    App.tsx
    pages/
    components/
    state/
    services/api/
    styles/index.css
  tests/
```

## Installation (to be executed once scaffolding tasks are generated)
```
pnpm install
```
(Dependencies: react, react-dom, react-router-dom, @tanstack/react-query, zustand, lightweight-charts, tailwindcss, postcss, autoprefixer, class-variance-authority, typescript, vitest, @testing-library/react)

## Development Scripts (planned package.json)
| Script | Purpose |
|--------|---------|
| dev | Start Vite dev server |
| build | Production build |
| test | Run unit/integration tests (vitest) |
| typecheck | tsc --noEmit |
| lint | ESLint + style checks |

## Environment Variables
```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```
Adjust for reverse proxy or staging.

## Fetch Layer Pattern
Minimal wrapper returning Result<T,Error>:
```ts
interface ApiError { status: number; message: string }
export async function apiGet<T>(path: string): Promise<T> { /* ... */ }
```
React Query integrates with keys: ['chart',symbol,range], ['backtest','status',id], etc.

## State Management
Zustand store slices:
- chartSlice: symbol, dateRange, indicators
- backtestSlice: lastConfig, selectedRunId, runHistory[]

## Styling & Theming
Tailwind + CSS variables for semantic tokens:
```css
:root { --color-equity:#3b82f6; --color-drawdown:#ef4444; }
.dark { --color-equity:#60a5fa; }
```

## Running Brain Locally
Ensure backend provides endpoints:
- GET /api/v1/chart
- POST /api/v1/backtest/run
- GET /api/v1/backtest/status/{id}
- GET /api/v1/backtest/result/{id}
- GET /api/v1/backtest/montecarlo/{id}

## Test Strategy
- Unit: pure utils (indicator param coercion), store reducers/selectors
- Integration: form submit triggers mocked network calls
- Contract: JSON schema validation against stored schema snapshots in `specs/006-begin-work-on/contracts/`
- Performance: micro benchmark (Monte Carlo overlay) ensures <300ms target
- Visual: Playwright scaffold (`npm run test:visual`) – requires running `npm run dev` separately; tests skip if server absent

### Running Visual Tests
1. In one terminal: `npm run dev`
2. In another: `npm run test:visual`
3. Baseline screenshots stored under `alphaforge-mind/tests/visual/__screenshots__/` (not yet asserted for pixel diff – future enhancement)

## Accessibility Checklist
- All interactive elements reachable by Tab
- Form errors use aria-describedby
- Chart focus mode toggles a data inspector with last-highlit bar values announced

## Performance Tips
- Avoid reconstructing chart instance; prefer setData/update
- Batch Monte Carlo overlay draws with rAF (T044, refined T055)
- Memoize derived arrays with referential stability (EquityCurve & MonteCarlo overlay)
- Use feature flags to disable extended calculations when unnecessary

## Feature Flags & Extensions
- `VITE_ENABLE_EXTENDED_PERCENTILES=true` exposes extended percentile toggle UI (T046, T051)
- `VITE_ENABLE_ADVANCED_VALIDATION=true` enables sensitivity/regime flag placeholders (T047, T051)

## Extending Indicators
Add type to IndicatorType union + param form metadata → register overlay provider.

## Screenshots (Placeholders)
Insert real captures after stable styling:
- Chart Analysis baseline: `![Chart Analysis](./images/chart-analysis-baseline.png)`
- Backtest Results (Equity + Metrics): `![Backtest Results](./images/backtest-results-baseline.png)`
- Monte Carlo Overlay: `![Monte Carlo](./images/montecarlo-overlay.png)`

## Validation Run (T059 placeholder)
Will append run metrics & test summary after executing full suite.

### Validation Run Summary (T059)
Date: 2025-09-27
Commit Branch: 006-begin-work-on

Test Suite (Vitest):
- Files: 26
- Tests: 48
- Passed: 48
- Failed: 0
- Monte Carlo perf (200 paths) render measurement: ~58ms (slightly above ideal 50ms target; within <300ms budget). Further optimization possible via off-main-thread canvas or WebGL (deferred).

Visual Tests (Playwright):
- Config present (playwright.config.ts)
- Baseline smoke spec skipped if dev server not running.

Feature Flags Verified:
- Extended percentiles & advanced validation toggles behind environment flags.

Next Optimization Candidates:
- Investigate percentile sorting optimization (currently O(P log P) per time index) via partial selection algorithm.
- Consider requestAnimationFrame time-slicing for equity + Monte Carlo concurrent renders.

All polish tasks T054–T059 marked complete.

## Next Step
Run `/tasks` to generate actionable tasks scaffolding the actual filesystem additions.
