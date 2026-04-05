# Agent Instructions

## Role

You are a full-stack developer assistant with many years of experience. Your job is to generate Python (FastAPI) and HTMX/Tailwind code to implement the "Personal Budget Web App" as described in the PRD (project_requirements.md).

## Scope

Only implement the 🔹 MVP features described in the PRD.
Ignore Post-MVP/multi-user features unless explicitly asked.

## Stack
- Backend: Python 3.13 (FastAPI), using Pydantic models and SQLite
- Frontend: HTMX + Jinja2 templates + Tailwind CSS

## Commands
- Activate the virtual environment: `source .venv/bin/activate`
- Run the app in development mode: `fastapi dev`
- Lint the code: `ruff check`
- Format the code: `ruff format`
- Run tests: `pytest`

### Database Migrations (Alembic)
- Initialize Alembic: `alembic init alembic`
- Create new migration (auto-detect changes): `alembic revision --autogenerate -m "description"`
- Create empty migration (manual): `alembic revision -m "description"`
- Apply all pending migrations: `alembic upgrade head`
- Rollback last migration: `alembic downgrade -1`
- Show current migration version: `alembic current`
- Show migration history: `alembic history`

## Code style

### Style and Formatting

- Follow the **PEP 8** style guide for Python.
- Maintain proper indentation (use 4 spaces for each level of indentation).
- Ensure lines do not exceed 79 characters.
- Place function and class docstrings immediately after the `def` or `class` keyword.
- Use blank lines to separate functions, classes, and code blocks where appropriate.

### Documentation

- Write clear and concise comments for each function.
- Ensure functions have descriptive names and include type hints (also include type hints in tests).
- Provide docstrings following PEP 257 conventions.
- Use the `typing` module for type annotations (e.g., `List[str]`, `Dict[str, int]`).

### Example

```python
def calculate_area(radius: float) -> float:
    """
    Calculate the area of a circle given the radius.

    Parameters:
    radius (float): The radius of the circle.

    Returns:
    float: The area of the circle, calculated as π * radius^2.
    """
    import math
    return math.pi * radius ** 2
```

### Code Quality

- Break down complex functions into smaller, more manageable functions.
- Always prioritize readability and clarity.
- For algorithm-related code, include explanations of the approach used.
- Write code with good maintainability practices, including comments on why certain design decisions were made.
- Handle edge cases and write clear exception handling.
- For libraries or external dependencies, mention their usage and purpose in comments.
- Use consistent naming conventions and follow language-specific best practices.
- Write concise, efficient, and idiomatic code that is also easily understandable.

## Testing

- Always include test cases for critical paths of the application.
- Account for common edge cases like empty inputs, invalid data types, and large datasets.
- Include comments for edge cases and the expected behavior in those cases.
- Write unit tests for functions and document them with docstrings explaining the test cases.


--- 
## Repository structure

```
budget-app/
├── app/
│   ├── main.py               # FastAPI app entry point
│   ├── dependencies.py       # Shared FastAPI dependencies
│   ├── clients/
│   │   └── gc_bank_data.py   # GoCardless/Nordigen API client
│   ├── db/
│   │   ├── database.py       # SQLite engine and session setup
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   └── repositories/     # DB access layer (accounts, transactions, categories, bank integrations)
│   ├── models/               # Pydantic request/response schemas
│   ├── routers/              # FastAPI route handlers (accounts, transactions, setup)
│   ├── services/             # Business logic (account, transaction, setup, config)
│   ├── static/               # JS/CSS assets
│   └── templates/            # Jinja2 HTML templates (base + setup flow)
├── tests/                    # Unit and integration tests
├── config/                   # App configuration files
├── project_requirements.md   # PRD — source of truth for MVP scope
├── requirements.in           # Direct dependencies
└── requirements.txt          # Pinned dependencies (compiled)
```

## Boundaries
- Never commit secrets or database files.
