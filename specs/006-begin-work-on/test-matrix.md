# Test Matrix (Feature 006 AlphaForge Mind)

| FR | Description (abridged) | Test Type(s) | Notes |
|----|------------------------|--------------|-------|
| FR-001 | Load candlestick chart | Integration (page load), Contract (candles schema), Unit (transform) | Mock candles endpoint |
| FR-002 | Add/remove indicators | Unit (indicator param logic), Integration (UI toggle) | Persist state test |
| FR-003 | Backtest form fields | Unit (validation), Integration (form render) | Single ticker enforcement |
| FR-004 | Input validation errors | Unit (validators), Integration (submission blocked) | Edge: end<start |
| FR-005 | Run Test submission | Integration (submit -> status poll), Contract (request schema) | Simulated API |
| FR-006 | Status progress | Integration (status states), Unit (state store) | Polling timing mocked |
| FR-007 | Display metrics & equity | Contract (result schema), Integration (render) | Equity length assertion |
| FR-008 | Validation outputs | Contract (validation fragment), Integration (panels toggle) | Walk-forward splits count |
| FR-009 | Monte Carlo visualization | Integration (render placeholder), Performance (paths render under cap) | 200 default paths |
| FR-010 | Run history switch | Unit (store history), Integration (select run) | Deterministic update |
| FR-011 | Persist last config | Unit (localStorage adapter), Integration (reload restores) | Session only |
| FR-012 | Error handling | Integration (error banner), Unit (error parser) | Backend 422 & 500 |
| FR-013 | Dynamic strategy params | Unit (strategy param builder), Integration (strategy change resets) | Compare defaults |
| FR-014 | Risk inputs presence | Unit (schema presence), Integration (form fields) | Additional risk future |
| FR-015 | Export configuration | Unit (serializer), Integration (modal JSON) | Snapshot test |
| FR-016 | Refresh chart reapply overlays | Integration (refresh action) | Indicator state retained |
| FR-017 | Percentile bands toggle | Integration (bands on/off), Contract (p5/p95 presence) | Extended percentiles future |
| FR-018 | Walk-forward segmentation view | Integration (splits chart/list) | Splits count matches payload |
| FR-019 | Deterministic run mapping | Unit (selector logic), Integration (switch runs no bleed) | Run id isolation |
| FR-020 | Slow response notice | Unit (timer threshold), Integration (delay simulation) | One-time notification |
| FR-021 | Long date span warning | Unit (span calc), Integration (confirmation modal) | >5y proceed allowed |
| FR-022 | Monte Carlo default 200 paths | Unit (config), Integration (initial render count) | Adjustable slider |
| EXT-PCT | Extended percentiles (alpha) | Contract (alpha2 schema), Skipped by default | Only when extended present |
| EXT-VAL | Sensitivity/regime toggles | Unit (flag handling), Integration (conditional UI) | Optional; behind feature flag |

## Coverage Summary
- Core FRs: All mapped to at least one integration test + optional unit layer.
- Contracts: JSON schema validation for candles, run-request, result, montecarlo (v1 + v1alpha2 optional cases).
- Performance: Monte Carlo render time (smoke benchmark) + initial chart render under target.
- Accessibility (implicit): Separate checklist (tab order, aria labels) to be added in tasks.

## Future Additions (Deferred)
- Visual regression (Playwright screenshot baseline) for Candle + Monte Carlo charts.
- SSE streaming tests (future feature).
