# Agent Instructions

Personal Budget Web App — see `project_requirements.md` (PRD) for scope and
`README.md` for the "why".

## Scope
- Implement only the 🔹 MVP features in the PRD.
- Ignore Post-MVP / multi-user features unless explicitly asked.

## Stack
- Backend: Python 3.13, FastAPI, Pydantic, SQLAlchemy + SQLite
- Frontend: HTMX + Jinja2 + Tailwind CSS
- Bank data: GoCardless/Nordigen API

## Commands
Prefix commands with `uv run` (no manual venv activation needed).
- `uv run fastapi dev` — run in development
- `uv run ruff check` / `uv run ruff format` — lint / format
- `uv run pytest` — run tests
- `uv run alembic revision --autogenerate -m "..."` then `uv run alembic upgrade head` — migrate

## Conventions
- Line length 88. Ruff lint rules are pinned in `pyproject.toml` (`select`).
- Prefer `pathlib.Path` over `os.path`/`open()` for filesystem work.
- Timezone-aware datetimes only: `datetime.now(UTC)`, never bare
  `datetime.now()` (ruff DTZ005). Store timestamps in UTC.
- Catch specific exceptions, not blind `except Exception` (ruff BLE001).
  Chain with `raise NewError(...) from e` when translating to a domain error.
  A blind catch is only acceptable to keep a non-critical step from failing
  the whole operation — log the traceback and add `# noqa: BLE001`.

## Boundaries
- Never commit secrets or database files.
