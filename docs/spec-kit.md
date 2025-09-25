# Spec Kit Workflow & Tooling Enhancements

This document describes the Spec-Driven Development helper scripts ("spec kit") and the 2025-09-23 enhancements.

## Goals
- Fast, repeatable creation of feature scaffolds (branch + spec directory)
- Enforce numbered, additive feature branch naming (e.g. `004-feature-keywords`)
- Provide machine-friendly JSON output for downstream automation
- Minimize accidental branch/filesystem mutations via dry-run mode
- Auto-populate spec template metadata (feature name, date, arguments)

## Updated Script: `create-new-feature.ps1`
Location: `.specify/scripts/powershell/create-new-feature.ps1`

### New Flags
| Flag | Purpose | Side Effects |
|------|---------|--------------|
| `-DryRun` | Preview branch name & feature number without creating branch or files | No filesystem or git mutations; JSON omits `SPEC_FILE` path (null) |
| `-NoBranch` | Create spec directory & file but skip git branch creation | Still writes spec (unless `-DryRun`) |
| `-Json` | Machine-readable output (compressed JSON) | Adds new fields (see below) |

### New JSON Fields
| Field | Description |
|-------|-------------|
| `RAW_DESCRIPTION` | Original feature description string (joined) |
| `DRY_RUN` | Indicates whether script ran in dry-run mode |
| `BRANCH_CREATED` | True only if git branch actually created |
| `SPEC_FILE` | Absolute path to spec (null in dry-run) |

### Auto-Template Interpolation
When the spec file is created from `.specify/templates/spec-template.md` the placeholders are replaced:
- `[FEATURE NAME]` → raw feature description
- `` `[###-feature-name]` `` → computed branch name (keeps backticks)
- `[DATE]` → ISO date (yyyy-MM-dd)
- `"$ARGUMENTS"` → original feature description (escaped quotes)

If interpolation fails, the template is still copied and a warning is emitted.

### Usage Examples
```
# Preview only
./.specify/scripts/powershell/create-new-feature.ps1 -DryRun "Permutation robustness scoring"

# Create fully (branch + spec) with JSON output
./.specify/scripts/powershell/create-new-feature.ps1 -Json "Add bootstrap validation module"

# Create spec without branch (e.g., working in detached state)
./.specify/scripts/powershell/create-new-feature.ps1 -NoBranch "Exploratory research: walk-forward refinement"
```

### Exit Behaviors
- Missing description → usage error (non-zero exit)
- Dry run skips: branch checkout + directory write + template copy
- No git repo detected: warning, branch creation skipped

## Related Helper Scripts (Unchanged)
- `get-feature-paths.ps1`: Emits key paths for current feature branch
- `check-prerequisites.ps1`: Validates presence of spec/plan/tasks docs
- `update-agent-context.ps1`: Synchronizes multi-agent context files

## Roadmap (Potential Future Improvements)
- `new-plan` command to derive initial `plan.md` from spec automatically
- Validation hook to refuse spec creation if uncommitted changes present (unless `-Force`)
- Optional `--Slug <override>` flag for custom branch slug beyond first 3 words
- Automatic CHANGELOG fragment stub creation when spec generated

## Maintenance Notes
- Keep template path consistent: `.specify/templates/spec-template.md`
- Prefer additive flags; do not change existing flag semantics without major version notice
- Ensure JSON additions are backward compatible (only additive keys)

---
Maintainer: Update this file when introducing new automation flags or behavioral changes.
