# Constitution Waivers

Use this file to record temporary, time-bound exceptions to constitution principles.

## Format
```
## WAIVER: <ID>
Principle: <Principle Name>
Scope: <files / modules>
Rationale: <why needed>
Risk: <impact if prolonged>
Mitigations: <steps to reduce risk>
Expires: YYYY-MM-DD (mandatory)
Owner: <name/alias>
Status: ACTIVE|EXPIRED|REVOKED
```

## Active Waivers

## WAIVER: W-T064-ADAPTER-SHIMS
Principle: Minimize Legacy Shims
Scope: alphaforge-brain/src/services/adapters/trades.py
Rationale: Retain adapter layer while parity tests (T070/T095) mature and clients migrate.
Risk: Confusion due to dual trade model paths; drift if adapters receive fixes.
Mitigations: Mark module deprecated; add tests to ensure non-export of legacy types (T095); roadmap timeline below.
Expires: 2026-01-31
Owner: core
Status: ACTIVE

Timeline: Deprecate in next minor; remove after one release cycle post T070 completion. If external consumers still depend, extend with explicit justification; otherwise delete module and update docs (T071,T073).
