# Feature Specification: Unified One-Command Launch CLI

**Feature Branch**: `007-unified-one-command`
**Created**: 2025-10-01
**Status**: Draft
**Input**: User description: "Unified one-command AlphaForge launch CLI: automatic port selection, readiness detection, browser open, headless flag, verbose diagnostics, researcher friendly UX"

## Execution Flow (main)
```
1. Parse feature description (done)
2. Extract key concepts: one-command launch, automatic ports, readiness, browser automation, headless mode, verbose diagnostics, non-technical user
3. Identify ambiguities → mark with [NEEDS CLARIFICATION] where present
4. Define user scenarios (primary + acceptance + edge)
5. Generate functional requirements (testable, business focused)
6. Clarify Brain vs Mind responsibilities to avoid leakage
7. Run review checklist; leave markers if unresolved
8. Output spec for planning
```

---

## ⚡ Quick Guidelines
Focus: Provide a frictionless startup experience for finance researchers (non-developers) to explore AlphaForge without memorizing multiple commands or troubleshooting environment quirks.

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
A finance researcher with limited technical background wants to explore AlphaForge backtesting and visualization. They should double‑click a shortcut or run a single command (e.g., `launch-alphaforge`) and be automatically taken to the UI once both backend and frontend are healthy—without editing config files or understanding ports.

### Acceptance Scenarios
1. **Given** a clean workstation with prerequisites installed (Python + Node), **When** the user runs `launch-alphaforge`, **Then** the backend and frontend start, health/readiness are confirmed, a browser tab opens at the correct UI URL, and a clear status summary is shown.
2. **Given** the default frontend port (5173) is already in use, **When** the user runs the command, **Then** the tool selects the next available port, reports the fallback choice, and still opens the UI successfully.
3. **Given** the user supplies `--no-browser`, **When** the command completes startup, **Then** no browser opens and the terminal displays the exact URL to copy.
4. **Given** the backend fails to start (e.g., import error), **When** the user runs the command, **Then** the tool clearly reports the failure cause and exits with a non‑zero code.
5. **Given** the user requests verbose diagnostics (`-v`), **When** startup proceeds, **Then** additional structured details (resolved paths, selected ports, detection steps) are printed.
6. **Given** the frontend takes longer than the readiness timeout, **When** timeout expires, **Then** the tool stops both processes and provides guidance (e.g., “Check Node install / firewall”).

### Edge Cases
- Port collisions on multiple sequential ports (exhausting fallback range).
- Missing Node or npm not on PATH (report actionable remediation steps).
- Browser open failure (headless server or locked down environment) → suggest manual URL.
- Slow backend dependency import causing perceived “hang” → spinner + periodic progress notes.
- IPv6-only or localhost vs 127.0.0.1 binding differences.
- User interrupts with Ctrl+C mid-start: both child processes terminate cleanly.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-CLI-001**: System MUST provide a single executable entrypoint `launch-alphaforge` accessible via Poetry script and PowerShell wrapper.
- **FR-CLI-002**: System MUST start backend (Brain) and frontend (Mind) processes in parallel and detect readiness via both port probing and HTTP health/landing checks.
- **FR-CLI-003**: System MUST automatically select a free frontend port if the preferred port is occupied and announce the final port before opening the browser.
- **FR-CLI-004**: System MUST open the default browser to the determined frontend URL unless `--no-browser` is supplied.
- **FR-CLI-005**: System MUST provide command-line flags for `--backend-port`, `--frontend-port`, `--no-browser`, and a verbosity flag `-v/--verbose` (detailed diagnostics).
- **FR-CLI-006**: System MUST exit with non-zero status if either service fails to become ready within a configurable timeout (default ≤ 60s) and MUST display succinct remediation guidance.
- **FR-CLI-007**: System MUST stream readable, prefixed logs (e.g., `[backend]`, `[frontend-log]`) and show a spinner or periodic status while waiting.
- **FR-CLI-008**: System MUST gracefully terminate both child processes on Ctrl+C or internal failure.
- **FR-CLI-009**: System SHOULD detect and clearly report missing prerequisites (Python version mismatch, npm absent) with actionable steps.
- **FR-CLI-010**: System SHOULD provide a quiet mode (inverse of verbose) for minimal output. [NEEDS CLARIFICATION: Is quiet mode required in v1?]
- **FR-CLI-011**: System SHOULD ensure deterministic environment validations (version drift hints) without blocking startup (soft warnings).
- **FR-CLI-012**: System SHOULD allow future extension for “profiles” (e.g., `--profile research`) without breaking the core interface (reserved flag handling).

### Cross-Project Boundary
- Brain (backend) responsibility: expose a lightweight `/health` endpoint and stable startup semantics; no knowledge of launcher flags.
- Mind (frontend) responsibility: standard Vite dev server; no backend orchestration logic embedded.
- Launcher responsibility: orchestration, port selection, readiness, UX messaging—not business logic, caching, or domain computation.

### Key Entities
(Runtime oriented; not persisted data)
- **Launch Session**: Transient context capturing chosen ports, start timestamps, and readiness outcomes.
- **Readiness Probe**: Composite check (socket + HTTP) whose success triggers browser open.

---

## Review & Acceptance Checklist

### Content Quality
- [ ] No implementation details leak (verify after refinement)
- [x] Focused on user value and experience
- [x] Written for non-technical stakeholders
- [x] Mandatory sections completed

### Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain (currently: quiet mode scope)
- [x] Requirements are testable
- [x] Success criteria measurable (readiness, exit codes, flags)
- [x] Scope bounded (orchestration only)
- [x] Dependencies & assumptions identified (Python, Node, health endpoint)
- [x] Brain/Mind boundary defined

---

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [ ] Review checklist passed (pending quiet mode decision)

---

## Open Questions
1. Quiet mode requirement for initial version? (If yes, add `--quiet` and define output suppression rules.)
2. Desired default timeout (current code uses 35–45s). Should spec enforce 45s default with `--timeout` flag? (Not yet in FR list explicitly.)
3. Should environment drift warnings (e.g., NumPy pin mismatch) surface at launch preface? (If yes, integrate optional pre-flight check.)

## Acceptance Test Outline (Mapping)
- AT-1 ↔ FR-CLI-001/002/004 readiness & browser
- AT-2 ↔ FR-CLI-003 port fallback
- AT-3 ↔ FR-CLI-004/005 `--no-browser`
- AT-4 ↔ FR-CLI-006 failure exit path
- AT-5 ↔ FR-CLI-005/007 verbose diagnostics
- AT-6 ↔ FR-CLI-006 timeout handling
- Edge Cases list ↔ FR-CLI-007/008/009

---

## Success Metrics
- Time from command invocation to UI availability ≤ 10s on a warm machine (non-binding stretch; not formal FR).
- Zero unhandled tracebacks during nominal startup/shutdown.
- User confusion rate (subjective feedback) reduced vs multi-command manual instructions (post‑rollout survey baseline).

---

## De-Scope / Not In v1
- Profile-based resource modes (only reserved flag placeholder).
- Auto-upgrade or dependency installation.
- Remote cluster orchestration (local only).

---

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Port race conditions | Startup flakiness | Atomic bind test & fallback scan |
| Buffered logs hide readiness | User perceives hang | Force line-buffer capture & periodic status prints |
| Missing npm | Immediate failure | Clear remediation message & exit code 1 |
| Browser launch blocked | UX break | Graceful fallback message with URL |
| Future flag creep | Complexity | Reserve namespace & keep FR minimal |

---

## Next Steps After Spec Approval
1. Implement missing flags (`-v`, maybe `--timeout`, optional `--quiet`).
2. Add integration test script (smoke) verifying exit code & readiness regex.
3. Update README Quick Start section referencing this feature (link to spec path).
4. Add CHANGELOG entry.
5. (Optional) Pre-flight environment drift warning integration.

---
