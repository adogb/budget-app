# Plan 01: API + React skeleton

Status: **approved** (2026-09-26).
Spec: [`spec.md`](../spec.md) §5, §6, §8 slice 1.

## Goal

Replace the Jinja/HTMX app with two parts:

- a FastAPI **JSON API** in feature folders, on a fresh database;
- a **React app** that calls it.

The app has no new features. At the end, the transactions page loads and shows
"No transactions yet". Real data arrives in slice 2 (bank flow).

This slice is delivered as **two PRs**, so each one stays reviewable:

- **PR A, backend:** restructure plus a JSON API. It can be tested on its own
  through pytest and `/docs`.
- **PR B, frontend:** the React skeleton on top of PR A.

## Scope

**In scope**
- Feature folders; the repository layer and service classes are replaced by
  plain functions.
- `User` and `user_id` removed. `Category` removed (it comes back in slice 3).
- A fresh database with one new initial migration. Alembic, not `create_all`,
  becomes the only way the schema is created.
- `GET /api/accounts` and `GET /api/transactions`, with money sent as
  `{amount, currency}`.
- The React app: layout and navigation, a transactions page, and an empty
  state.
- FastAPI serves the built React app. `REVIEW.md` is created and `AGENTS.md`
  updated.

**Out of scope (slice 2)**
- Any bank routes (linking, sync), import fixes and pending transactions.
- The bank code is **moved and simplified** here but keeps its current
  behaviour. Its tests prove that.

## PR A: Backend

### Target layout

```
app/
  main.py              create app, include routers, serve frontend/dist
  config.py            DATABASE_URL, BUDGET_CURRENCY = "DKK", GoCardless secrets
  db.py                engine, SessionLocal, get_db()
  models.py            all SQLAlchemy models: Account, BankIntegration, Transaction
  money.py             Money schema {amount: int, currency: str}
  accounts/
    routes.py          GET /api/accounts
    service.py         list_accounts(db)
    schemas.py         AccountOut
  transactions/
    routes.py          GET /api/transactions?account_id=
    service.py         list_transactions(db, account_id=None)
    schemas.py         TransactionOut
  bank/
    client.py          GoCardless client (moved from app/clients/)
    client_models.py   (moved), gc_bank_data_oapi.json (moved)
    linking.py         from setup_service.py + bank_integration_repository.py
    sync.py            from sync_service.py + the queries it needs
    errors.py          BankAPIError and its exception handler
tests/
  conftest.py          shared in-memory database fixture
  test_accounts_api.py  test_transactions_api.py
  bank/test_linking.py  bank/test_sync.py   (adapted from the existing tests)
```

**Removed:**
- `app/routers/`, `app/services/`, `app/db/repositories/`, `app/dependencies.py`
- `app/templates/`, `app/static/`, `app/models/` (the Pydantic models move into
  each feature's `schemas.py`)
- `alembic/versions/*` (replaced by a new initial migration)

**Why plain functions instead of service classes:** a class holding `db` and
`user_id` adds a layer, and with a single user there's nothing left to hold.
`list_transactions(db, account_id)` reads top to bottom, and tests just pass a
session in.

### Order of work

1. `config.py`, `db.py`, `models.py`:
   - Models: drop `User` and `user_id`, drop `Category` and
     `Transaction.category_id`, keep `currency` everywhere.
   - Remove `init_db()` from startup.
2. Alembic: point `env.py` at `app.models`, delete the old versions, then run
   `alembic revision --autogenerate -m "initial schema"`.
   Move `db/budget.db` aside to `db/budget-old.db` (git-ignored, recoverable)
   and run `alembic upgrade head`.
3. `tests/conftest.py`: an in-memory database built with
   `Base.metadata.create_all`. Tests don't need migrations.
4. `bank/`: move the client, then fold `setup_service` plus its repository into
   `linking.py`, and `sync_service` plus its queries into `sync.py`, as
   functions. Adapt the existing 23 bank tests. They must pass with the same
   assertions, apart from `user_id`.
5. `money.py`, then `accounts/` and `transactions/` (schemas → service →
   routes), then `main.py`.
6. Static serving: if `frontend/dist` exists, serve its files, and answer any
   non-`/api` path with `index.html`, so a refresh on `/transactions` works.
7. Dependencies:
   - Remove `black`, `nordigen` (unused) and `jinja2`.
   - Move `pytest` and `ruff` to `[dependency-groups] dev`.
8. `AGENTS.md` (stack, layout, commands) and a new `REVIEW.md` (see below).

### Tests that prove it

| Test | Proves |
|---|---|
| `test_transactions_api::test_empty` | `GET /api/transactions` → `200 []` |
| `test_transactions_api::test_lists_newest_first` | Rows come back sorted by `booking_date` descending, with `amount: {amount: -2500, currency: "DKK"}` |
| `test_transactions_api::test_filter_by_account` | `?account_id=` only returns that account's rows |
| `test_accounts_api::test_lists_accounts` | Balance is returned as Money |
| `bank/test_sync.py`, `bank/test_linking.py` | The existing behaviour is unchanged after the move |
| `test_main::test_spa_fallback` | `GET /transactions` returns `index.html` when `dist` exists; `/api/unknown` returns 404 |

On top of that: `uv run ruff check`, `uv run ruff format --check`, and a check
that `alembic upgrade head` on an empty database matches the models.

## PR B: Frontend

### Tooling

- **Node:** upgrade to 24.15 or newer first. Your npm 12 refuses Node 24.14.1.
- **Scaffold:** `npm create vite@latest frontend -- --template react-ts`, then
  delete the demo content.
- **Dependencies:** `react-router`, `@tanstack/react-query`, `tailwindcss` and
  `@tailwindcss/vite`.
- **Dev dependencies:** `openapi-typescript`, `vitest`.
- **API types:** `npm run gen:api` calls a small Python command that writes
  `app.openapi()` to `frontend/openapi.json`, then generates
  `src/api/schema.d.ts`. No running server needed. Both files are committed,
  so the diff shows when the API changes.

### Layout

```
frontend/
  vite.config.ts        React + Tailwind plugins; proxy /api → localhost:8000
  src/
    main.tsx            createRoot, <QueryClientProvider>, <BrowserRouter>
    App.tsx             page layout (header + nav) and <Routes>
    pages/
      TransactionsPage.tsx   fetch with useQuery, show loading / error / empty / table
    components/
      Money.tsx         <Money value={...} />, formatted with Intl.NumberFormat
    api/
      schema.d.ts       generated, never edited by hand
      client.ts         getJson<T>(path): fetch + error on non-2xx (~10 lines)
      transactions.ts   fetchTransactions(), typed from schema.d.ts
    lib/money.ts        formatMoney() + money.test.ts
```

### Order of work

1. Scaffold, Tailwind and the proxy. The empty page renders.
2. `gen:api` and `api/client.ts`.
3. `main.tsx` providers, the `App.tsx` layout, and one route: `/` redirects to
   `/transactions`.
4. `formatMoney` with its test, then `Money.tsx`.
5. `TransactionsPage`, covering all four states.
6. `npm run build`, then check that `uv run fastapi run` serves the app on :8000.

### Tests that prove it

| Check | Proves |
|---|---|
| `money.test.ts` | `-250000 DKK` → `-2.500,00 kr.`; `0` and positive amounts format correctly |
| `npm run build` | TypeScript compiles, including the generated API types |
| Browser check (me, with Playwright) | The page loads, shows "No transactions yet" and navigation works. With a few rows inserted by hand, the table renders and amounts are formatted. Screenshots go in the PR. |

I'm not adding committed Playwright tests in this slice. There's no user flow
worth protecting yet, so they start in slice 2 with bank linking.

### React concepts in this PR

Read these in roughly this order. Each has one line on where it shows up.

| Concept | Where you'll see it |
|---|---|
| [Your first component](https://react.dev/learn/your-first-component) | Every `.tsx` file exports one function component |
| [Writing markup with JSX](https://react.dev/learn/writing-markup-with-jsx) | The HTML-like syntax in `App.tsx` and the page |
| [Passing props to a component](https://react.dev/learn/passing-props-to-a-component) | `<Money value={t.amount} />` |
| [Conditional rendering](https://react.dev/learn/conditional-rendering) | Loading / error / empty / table in `TransactionsPage` |
| [Rendering lists](https://react.dev/learn/rendering-lists) | `transactions.map(...)` and why each row needs a `key` |
| [Rules of Hooks](https://react.dev/reference/rules/rules-of-hooks) | `useQuery` is a hook: call it at the top of a component |
| [You might not need an Effect: fetching data](https://react.dev/learn/you-might-not-need-an-effect#fetching-data) | Why we use TanStack Query instead of `useEffect` + `fetch` |
| [Using TypeScript](https://react.dev/learn/typescript) | Typing props, e.g. `{ value: Money }` |
| [Build a React app from scratch](https://react.dev/learn/build-a-react-app-from-scratch) | Why Vite, and what we're giving up by not using a framework |
| [`createRoot`](https://react.dev/reference/react-dom/client/createRoot) and [`<StrictMode>`](https://react.dev/reference/react/StrictMode) | `main.tsx`, where React takes over the page |

**Outside React:**
- [TanStack Query quick start](https://tanstack.com/query/latest/docs/framework/react/quick-start)
- [React Router declarative mode](https://reactrouter.com/start/declarative/installation)
- [Tailwind with Vite](https://tailwindcss.com/docs/installation/using-vite)

## `REVIEW.md` (new)

A short checklist that every PR is reviewed against:

- Money is an integer in minor units, never a float, and is sent as
  `{amount, currency}`.
- Datetimes are timezone-aware UTC (see `AGENTS.md`).
- `budget/calculations.py` imports nothing from FastAPI, SQLAlchemy or the
  frontend.
- No secrets and no `.db` files are committed.
- Every schema change comes with an Alembic migration.
- `frontend/src/api/schema.d.ts` is regenerated, not hand-edited.
- Frontend PRs link the React concepts they use.

## How to review

- **PR A:** read in this order:
  1. `app/models.py`
  2. `app/transactions/` (routes → service → schemas)
  3. `app/main.py`
  4. `app/bank/sync.py`, compared against the old `sync_service.py`

  The bank tests passing unchanged is the proof that nothing broke.
- **PR B:** read in this order:
  1. `main.tsx`
  2. `App.tsx`
  3. `TransactionsPage.tsx`
  4. `api/`

  Keep the React concepts table open alongside.

## Risks

- **Node/npm mismatch:** upgrade Node before PR B.
- **Temporary gap:** after PR A there's no way to link a bank or sync until
  slice 2. The old database is kept as `db/budget-old.db` in case you need
  anything from it.
