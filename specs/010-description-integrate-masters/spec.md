# Feature Specification: Advanced Statistical Validation Integration

**Feature Branch**: `010-description-integrate-masters`
**Created**: 2025-10-10
**Status**: Implementation Complete — Phase 3.5 polish merged, governance hand-off in progress (SLA tuning outstanding)
**Input**: User description: "advanced statistical validation
This specification proposes the integration of an advanced statistical validation layer on top of AlphaForge’s existing backtesting metrics to enhance the financial reliability and credibility of strategy results. Currently, the system reports standard performance measures (Sharpe, CAGR, Max Drawdown, Profit Factor, etc.) which are necessary but insufficient for determining true robustness. To address this, we introduce the Masters’ permutation test framework, as demonstrated in the referenced video, which forms the backbone of a scientifically defensible strategy validation process. Masters’ structure involves permuting bar-level data, re-optimizing across multiple randomized universes, and computing p-values to determine whether observed performance could arise by chance. This differs from conventional Monte Carlo equity resampling by testing the null hypothesis of no real edge, rather than merely the variability of returns. Implementing this within AlphaForge ensures each backtest is accompanied by in-sample and walk-forward permutation tests, yielding statistical confidence (e.g., p < 0.01) that results are not random artifacts. In addition, we extend the validation with Deflated Sharpe Ratio (DSR), Probabilistic Sharpe Ratio (PSR), and Combinatorially Symmetric Cross-Validation (CSCV) to control for multiple testing and selection bias. Incorporating Purged K-Fold or CPCV cross-validation further ensures temporal independence and eliminates label leakage. The rationale is to elevate AlphaForge from a deterministic simulator to a reproducible hypothesis testing framework, aligning with best practices in quantitative research. Financially, this transformation means performance metrics now carry statistical weight, preventing overfitting and false discovery. We also add execution realism through modeled transaction costs, market impact, and liquidity capacity tests to validate tradability under realistic constraints. By embedding these features into AlphaForge’s backend validation services and frontend visualization, every strategy evaluation becomes both repeatable and statistically defensible. The result is a unified workflow where a strategy must pass rigorous Masters-style permutation validation before being considered viable. This framework not only guards against data-mining bias but also enforces a quant discipline consistent with institutional research standards. In summary, adopting Masters’ structure formalizes the distinction between “looks profitable” and “statistically significant”, making AlphaForge a credible environment for genuine strategy discovery and verification."

## Execution Flow (main)
```
1. Parse user description from Input
	→ If empty: ERROR "No feature description provided"
2. Extract key concepts from description
	→ Identify: actors, actions, data, constraints
3. For each unclear aspect:
	→ Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
	→ If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
	→ Each requirement must be testable
	→ Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
	→ If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
	→ If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no concrete frameworks unless contract boundary required)
- 👥 Written for business stakeholders, not developers
- 🧩 If feature spans both backend (Brain) and frontend (Mind), clearly separate concerns: backend computation vs frontend presentation.

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave it as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question]
2. **Don't guess** missing contract interactions—ask.
3. **Think like a tester**: Each requirement must map to an observable outcome.
4. **Common underspecified areas**: permissions, data retention, performance targets, error handling, integration boundaries, security/compliance.

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a quantitative researcher using AlphaForge, I want each strategy run to include Masters-style permutation validation, bias-controlled Sharpe diagnostics, and tradability stress checks so that I can distinguish statistically significant edges from random artifacts before deploying capital.

### Acceptance Scenarios
1. **Given** a researcher submits a backtest with default validation enabled, **When** the run completes, **Then** the results include Masters permutation p-values for both in-sample and walk-forward windows alongside clear pass/fail guidance against a configurable significance threshold.
2. **Given** a strategy exhibits optimistic Sharpe after extensive parameter searches, **When** the new validation executes, **Then** Deflated Sharpe Ratio, Probabilistic Sharpe Ratio, and CSCV-adjusted metrics are calculated and stored, flagging runs that fall below institutional confidence benchmarks.
3. **Given** the researcher enables purged K-Fold validation, **When** the system sequences folds, **Then** label leakage windows are removed, CPCV fold outcomes are recorded, and a consolidated leakage score is surfaced in the API and UI.
4. **Given** a strategy trades illiquid instruments, **When** execution realism checks run, **Then** modeled transaction costs, market impact, and liquidity capacity metrics are added to the validation summary with explicit warnings if tradability limits are breached.
5. **Given** the Mind UI loads a completed run, **When** the user reviews validation results, **Then** the interface visualizes permutation distributions, Sharpe deflation bands, cross-validation fold outcomes, and execution realism diagnostics with tooltip explanations and correlation IDs for support follow-up.

### Edge Cases
- Runs with insufficient history for full permutation counts must fall back to minimum-sample heuristics and record the fallback path deterministically.
- Strategies that already include heavy transaction costs must prevent double-counting when execution realism overlays run; conflicts are reported clearly.
- Cross-validation folds that cannot meet purge spacing must downgrade to CPCV with a documented justification while preserving determinism.
- When the researcher disables specific validation modules, the manifest must still document the omission and the UI must indicate that the associated confidence score is unavailable.
- Large walk-forward optimization grids must reuse existing optimization deferral safeguards to keep runtime bounded while still producing statistical evidence for executed folds.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: System MUST execute Masters-style permutation tests for every completed backtest, covering both in-sample and any configured walk-forward segments, and persist per-segment p-values, effect sizes, and permutation summaries in validation artifacts and SQLite.
- **FR-002**: System MUST allow configurable significance thresholds (default 0.01) and label each run with `validation_significance` status (pass, caution, fail) based on Masters permutation outcomes.
- **FR-003**: System MUST re-optimise strategy parameters within each permutation universe when strategy settings require optimization, recording the chosen parameter set and ensuring deterministic seed derivation.
- **FR-004**: System MUST compute Deflated Sharpe Ratio (DSR) and Probabilistic Sharpe Ratio (PSR) for every run, persisting raw and adjusted Sharpe metrics along with the assumed trials count driving deflation.
- **FR-005**: System MUST run Combinatorially Symmetric Cross-Validation (CSCV) to estimate selection bias, emitting CSCV-adjusted performance statistics and a bias flag whenever the CSCV-adjusted Sharpe is ≤ (observed Sharpe − 0.25) **or** represents a ≥20% relative drop from the observed Sharpe.
- **FR-006**: System MUST support Purged K-Fold and Combinatorial Purged Cross-Validation (CPCV) modes, automatically purging overlapping samples to eliminate look-ahead leakage and recording purge windows per fold, using a default time-based embargo equal to the greater of 30 calendar days or the strategy’s lookback horizon unless explicitly overridden.
- **FR-007**: System MUST expose configuration controls allowing researchers to enable or disable each validation module (permutation, DSR, PSR, CSCV, Purged K-Fold, CPCV) while preserving deterministic defaults when omitted.
- **FR-008**: System MUST emit structured validation payloads over API and SSE containing permutation histograms, significance levels, Sharpe adjustments, cross-validation outcomes, and execution realism diagnostics for Mind and external clients.
- **FR-009**: System MUST integrate execution realism checks—deterministic transaction cost overlays, market-impact modeling, and liquidity capacity analysis—and flag runs exceeding configured cost or capacity budgets with actionable guidance that includes (a) cost and impact deltas vs. budget, (b) capacity ratio, and (c) at least one remediation recommendation (e.g., reduce size, slow execution, widen spreads).
- **FR-010**: System MUST propagate validation outcomes into retention and promotion policies so that runs failing significance or realism thresholds cannot be auto-promoted without an explicit override.
- **FR-011**: Mind MUST visualize new validation outputs (permutation distributions, confidence badges, Sharpe deflation summaries, cross-validation timelines, execution realism gauges) and link the correlation ID shown in the API response for troubleshooting.
- **FR-012**: API documentation MUST add new schemas or extend existing ones to cover validation significance, Sharpe adjustments, cross-validation outcomes, and execution realism metrics, including sample payloads and field descriptions.
- **FR-013**: System MUST maintain deterministic audit trails by logging seeds, permutation counts, cross-validation fold definitions, and execution realism assumptions within the manifest and SQLite records.
- **FR-014**: System MUST expose configuration metadata (e.g., permutations executed, fold counts, impact model chosen) via CLI/SDK helpers to support scripting and reproducibility audits.
- **FR-015**: System MUST treat validation modules as performance-gated tasks, measuring runtime and resource usage for permutations, cross-validation, and execution realism so CI can enforce guardrails or raise warnings when SLA thresholds are exceeded.
- **FR-016**: System MUST ensure backward compatibility by defaulting new validation outputs to neutral/waived states for historical runs, while providing migration guidance for backfilling when data is available.

### Cross-Project Boundary
- **Brain responsibilities**: orchestrate Masters permutation engines, Sharpe bias adjustments, cross-validation workflows, execution realism modeling, deterministic seeding, persistence, API/SSE payloads, and retention enforcement based on statistical outcomes.
- **Mind responsibilities**: present validation visualizations, significance badges, fold diagnostics, and realism alerts using supplied payloads; collect user preferences for module toggles; avoid implementing statistical calculations client-side.

### Key Entities
- **PermutationValidationResult**: encapsulates per-segment permutation metadata (seed root, permutations executed, p-values, effect sizes, outcome histogram references).
- **CrossValidationFold**: defines purged or CPCV fold boundaries, training/testing indices, optimized parameters, and per-fold performance metrics.
- **ExecutionRealismReport**: aggregates transaction cost, market impact, and liquidity capacity calculations, returning pass/fail status, budget utilization, and remediation guidance.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified
- [x] If dual project: Brain/Mind boundary defined

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

---
