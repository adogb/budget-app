# Agent Instructions

Personal envelope-budgeting web app. Read in order: `docs/intent.md` (why),
`docs/spec.md` (what), `docs/plans/` (how, one plan per slice).

## Workflow
- Implement only what the spec marks **Must/Should**, one slice at a time.
- No code without an approved plan in `docs/plans/`.
- Review every PR against `REVIEW.md`.

## Stack
- Backend: Python 3.13, FastAPI (JSON API under `/api`), Pydantic,
  SQLAlchemy 2.0 + SQLite, Alembic
- Frontend: React + TypeScript + Tailwind in `frontend/` (Vite)
- Bank data: GoCardless Bank Account Data

## Layout
- `app/models.py`: all tables. `app/db.py`: session and `DbSession`.
- One folder per feature (`app/accounts/`, `app/transactions/`, `app/bank/`),
  each with `routes.py` (HTTP), `service.py` (plain functions: logic and
  queries) and `schemas.py` (Pydantic). No repository layer, no service classes.

## Commands
Prefix Python commands with `uv run` (no manual venv activation needed).
- `uv run fastapi dev` — run the API in development
- `uv run ruff check` / `uv run ruff format` — lint / format
- `uv run pytest` — run tests (in-memory database, see `tests/conftest.py`)
- `uv run alembic revision --autogenerate -m "..."` then
  `uv run alembic upgrade head` — migrate. The schema is only ever created by
  Alembic.

Frontend, from `frontend/` (Node version in `.nvmrc`, run `nvm use`):
- `npm run dev` — Vite on :5173, proxies `/api` to the API on :8000
- `npm test` / `npm run lint` — Vitest / oxlint
- `npm run build` — type-check and build `dist/`, which `uv run fastapi run`
  serves on :8000
- `npm run gen:api` — regenerate `openapi.json` and `src/api/schema.d.ts`
  after any API change. TypeScript is pinned to 5.9 because
  `openapi-typescript` doesn't support 6 yet.

## Conventions
- Line length 88. Ruff lint rules are pinned in `pyproject.toml` (`select`).
- Money: integers in minor units (`*_minor` columns), sent as
  `{amount, currency}` (`app/money.py`). Parse bank amounts with
  `to_minor_units`, never `float`.
- Prefer `pathlib.Path` over `os.path`/`open()` for filesystem work.
- Timezone-aware datetimes only: `datetime.now(UTC)`, never bare
  `datetime.now()` (ruff DTZ005). Store timestamps in UTC.
- Catch specific exceptions, not blind `except Exception` (ruff BLE001).
  Chain with `raise NewError(...) from e` when translating to a domain error.
  A blind catch is only acceptable to keep a non-critical step from failing
  the whole operation — log the traceback and add `# noqa: BLE001`.

## Boundaries
- Never commit secrets or database files.
