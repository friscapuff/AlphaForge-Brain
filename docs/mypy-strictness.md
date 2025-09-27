# Mypy Strictness Reference

This document complements the brief policy section in the main `README.md`.

## 1. Enforcement Model
CI runs mypy with the repository `mypy.ini`. The job produces three key artifacts:
- `mypy_baseline.txt` – committed reference count (acts as an upper bound)
- `mypy_final.txt` – raw output from the current run
- `mypy_diff.md` – categorized delta (added/removed error codes)

A pull request may only reduce or keep constant the error count. Any increase fails the build. When the count decreases (e.g., refactor removes legacy ignores), update `mypy_baseline.txt` in that PR.

## 2. Error Code Categories We Track
| Category | Policy | Notes |
|----------|--------|-------|
| `unused-ignore` | Must remain zero | Indicates dead debt; remove immediately |
| `redundant-cast` | Should remain zero | Replace with proper typing or remove |
| `attr-defined` | Allowed only with justification | Prefer guards or `hasattr`+narrowing |
| `call-arg`, `arg-type` | Must be fixed | Usually Optional misuse or wrong param key |
| `return-value` | Must be fixed | Functions must honor declared contracts |
| `index`, `assignment` | Must be fixed | Signals container shape uncertainty |
| `import-not-found` | Avoid via vendored stubs or optional import guard | If library lacks types, add conditional import with runtime fallback |

## 3. Optional Dependencies Pattern
```python
try:
    import structlog
except Exception:  # pragma: no cover
    class structlog:  # type: ignore[no-redef]
        @staticmethod
        def get_logger():
            class _L:  # minimal stub
                def debug(self, *a: object, **k: object) -> None: ...
            return _L()
```
Keep stubs minimal; do not replicate full external API.

## 4. Ignoring With Purpose
Use granular codes: `# type: ignore[import-not-found]  # reason: 3rd_party_missing_typing`. Avoid piling multiple reasons on one line. Never use a bare `# type: ignore`.

## 5. Refactoring Playbook
1. Narrow Optional: introduce local guard, exit early.
2. Extract dynamic section: move complex `DataFrame` mutation into helper with precise signature.
3. Replace dict-of-misc: promote to `@dataclass` or Pydantic model when accessed in >2 places.
4. Remove speculative generics: only add generic `TypeVar` if truly reused with multiple concrete types.
5. Delete stale casts: rerun mypy; if green, commit.

## 6. Performance Considerations
Heavy unions or very large inferred types (e.g., thousands of literal columns) slow mypy. If a single module adds >1s incremental analysis time:
- Precompute TypedDict / Protocols instead of large literal dicts inline.
- Collapse repeated similar structures into a `NewType` or model class.
- Avoid deeply nested list/dict comprehensions with heterogeneous element types—build stepwise.

## 7. Raising the Baseline
When eliminating legacy errors:
1. Run `poetry run mypy > mypy_final.txt` locally.
2. Confirm removed codes in `mypy_diff.md` (run helper script if present).
3. Overwrite `mypy_baseline.txt` with the new `mypy_final.txt` subset or curated format.
4. Commit both changes in the same PR.

## 8. Future Enhancements
- Add `scripts/ci/verify_mypy_delta.py` to enforce zero-delta automatically.
- Generate an HTML summary with trends over last N commits.
- Integrate with pre-commit hook to block local commits introducing new errors.

---
Questions? Open an issue with label `typing`.
