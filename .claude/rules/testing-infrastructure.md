# Testing Infrastructure Rules (govtech-sniper)

## Python Linting (backend/)
- All Python code is checked by **ruff** (config: `backend/pyproject.toml`)
- `ruff check backend/app/` to lint, `ruff check --fix backend/app/` to auto-fix
- `ruff format backend/app/` to format
- Import sorting is handled by ruff's `I` rule — do not run isort separately
- `B008` is ignored for FastAPI's `Depends()` pattern
- SQLAlchemy comparisons (`== True`, `== None`) are ignored via E711/E712

## Python Type Checking (backend/)
- `pyright backend/app/` for type checking (basic mode, warn-only)
- 494 pre-existing errors — do not add new ones, but don't fix old ones unless in changed code

## TypeScript (frontend/)
- `npx tsc --noEmit` from `frontend/` to type check (uses incremental builds)
- **NEVER pass individual file paths to tsc** — it does not support single-file checking
- ESLint: `npm run lint` from `frontend/`

## Hook Behavior
- **Python edits**: ruff auto-formats + fixes imports, pyright warns (doesn't block)
- **TypeScript edits**: tsc runs whole-project check (blocks on failure), prettier formats
- **git commit**: pre-commit hook runs ruff + tsc on staged files (blocks on failure)
- Hook failures are **real errors** — fix them, don't ignore or bypass

## Before Every Commit
- Git pre-commit hook enforces ruff + tsc
- Never use `--no-verify` to bypass hooks
- If hook fails: fix errors, re-stage, retry commit

## Linting Commands Quick Reference
```bash
# Python
ruff check backend/app/               # Lint
ruff check --fix backend/app/         # Auto-fix
ruff format backend/app/              # Format

# TypeScript
cd frontend && npx tsc --noEmit       # Type check
cd frontend && npx prettier --write src/  # Format
cd frontend && npm run lint           # ESLint
```
