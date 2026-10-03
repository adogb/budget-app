# Review checklist

Every PR is reviewed against this list, by a separate review pass and by the
owner.

## Correctness
- Money is an integer in minor units, never a float, and is sent as
  `{amount, currency}`. Bank amounts go through `to_minor_units`.
- Datetimes are timezone-aware UTC.
- Every schema change has an Alembic migration, and `alembic check` passes.
- `uv run pyright` reports 0 errors. Handle values that may be `None` instead
  of silencing the checker.

## Structure
- `app/budget/calculations.py` imports nothing from FastAPI, SQLAlchemy or the
  frontend.
- New backend code follows the feature-folder layout in `AGENTS.md`.
- `frontend/src/api/schema.d.ts` is regenerated, not hand-edited.

## Understandable
- The PR description says where to start reading.
- Frontend PRs link the React concepts they use (react.dev).
- Behaviour changes are called out, even small ones.

## Safety
- No secrets and no `.db` files are committed.
- Tests never touch `db/budget.db` or call the real bank API.
