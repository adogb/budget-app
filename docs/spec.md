# Spec: envelope budgeting MVP

Status: **accepted** (2026-09-26).
Built from: [`intent.md`](intent.md). Decisions are recorded in §7.

## 1. Envelope model

This follows Actual Budget's envelope method. Amounts are integers in the
currency's minor unit (øre for DKK). The MVP budgets in DKK only (§7).

### Terms

| Term | Meaning |
|---|---|
| **Category group** | A folder of categories, e.g. "Housing". One kind of group holds **income** categories. |
| **Assigned** | Money you put into a category's envelope for a month. |
| **Activity** | The sum of your share of the transactions in that category and month (spending is negative). |
| **Available** | What's left in the envelope: `carryover + assigned + activity`. |
| **Carryover** | Last month's Available, if it's positive. A negative Available does not carry over. |
| **Overspent** | The sum of the negative Available amounts in a month. It is taken from the next month's Ready to Assign. |
| **Ready to Assign** | Money that hasn't been given a job yet. |

### Formulas

These live in one module of pure functions (`budget/calculations.py`). Nothing
is stored or cached: every page load recalculates from transactions and
assignments, which is fast enough for one person's data.

```
available(c, m)       = max(available(c, m-1), 0) + assigned(c, m) + activity(c, m)
overspent(m)          = sum of min(available(c, m), 0) over all categories   # ≤ 0
ready_to_assign(m)    = ready_to_assign(m-1)
                      + income(m)
                      + overspent(m-1)
                      - total_assigned(m)
```

The first month uses `ready_to_assign(start-1) = starting balances` (see §6).
If Ready to Assign goes negative, you've assigned more than you have, and it
shows in red.

### Worked example

This assumes a starting balance of 0 and a single category.

| Month | Income | Groceries: assigned / activity / available | Ready to Assign |
|---|---|---|---|
| Sep | 30 000 | 3 000 / −3 500 / **−500** (overspent) | 30 000 − 3 000 = 27 000 |
| Oct | 30 000 | 3 000 / −2 000 / 1 000 (the −500 is not carried over) | 27 000 + 30 000 − 500 − 3 000 = 53 500 |

## 2. Transactions, lines and the shared account

Every transaction has **one or more lines**, and the category lives on the
line, not on the transaction. A normal transaction has one line. A split
transaction has several.

Each line also has an **owner**: `me` or `roommate`. Only `me` lines count in
the budget.

| Case | Lines |
|---|---|
| Personal card payment, 250 kr groceries | `me · Groceries · −250` |
| Split personal purchase, 800 kr | `me · Groceries · −500`, `me · Household · −300` |
| Shared account purchase, 1 000 kr, 50/50 | `me · Groceries · −500`, `roommate · −500` |
| Roommate's contribution to the shared account, +3 000 | `roommate · +3 000` |
| My transfer from checking to the shared account | a **transfer** on both sides, with no category and no budget effect |

What follows from this:

- **Shared account ratio:** the shared account has a default ratio, e.g.
  `my_share = 0.5`. Imported shared transactions get their lines split using
  that ratio. You can change the ratio on any transaction, and payee rules can
  set a different ratio per category or payee (§4).
- **Roommate balance:** the sum of the `roommate` lines is the roommate's money
  in the shared account. "My balance" in that account is
  `account balance − roommate balance`. This is also the "settle up" number.
- **Transfers:** a transaction marked as a transfer has no category. In the
  MVP, marking is manual or done by a payee rule. Automatically pairing the two
  sides of a transfer is post-MVP.
- **Uncategorised lines:** `me` lines with no category show as a count on the
  budget screen ("12 uncategorised").

## 3. Features

Priority: **Must** = MVP, **Should** = MVP if cheap, **Later** = after MVP.

| # | Feature | Priority | Done when |
|---|---|---|---|
| F1 | Create, rename, reorder and hide category groups and categories | Must | I can build my own category tree in the UI |
| F2 | Budget month screen | Must | For any month I see assigned / activity / available per category and Ready to Assign, and can edit assigned inline |
| F3 | Move money between categories | Should | Covering overspending takes one action |
| F4 | Link bank, sync accounts and transactions | Must | Existing flow, rebuilt in React |
| F5 | Bank consent renewal | Must | I see when consent expires and can re-link without losing data |
| F6 | Transactions list with filters | Must | Filter by account, month, category, label, uncategorised and text |
| F7 | Fast categorising | Must | Keyboard-friendly category picker, bulk-assign selected rows, "next uncategorised" |
| F8 | Split transactions | Must | Split one transaction over several categories; the lines must add up to the total |
| F9 | Shared account ratio | Must | Default ratio per account, overridable per transaction, roommate balance shown |
| F10 | Payee rules | Must | "Description contains X → category Y / ratio Z / transfer" is applied on import; I can create a rule from a transaction |
| F11 | Labels | Should | Add free-form labels to transactions and filter by them |
| F12 | Manual transactions | Should | Add or edit a transaction by hand (cash, corrections) |
| F13 | Spending overview | Must | Spending per category per month for the last 6–12 months, plus income vs spending |
| F14 | Hold money for next month | Later | Actual's "hold for next month" |
| F15 | Carry overspending forward per category | Later | Actual's per-category rollover option |
| F16 | Auth and hosting | Later | Per the intent's non-goals |

## 4. Bank import

The existing GoCardless client and sync are kept. Their behaviour changes as
follows:

- **Pending transactions are kept separate.** Today pending and booked
  transactions are mixed. Pending ones change ID when they're booked, which
  creates duplicates. From now on:
  - Booked transactions go into `transactions`, as now.
  - Pending ones go into a `pending_transactions` table. It is emptied and
    refilled for that account on every sync, so the pending version simply
    disappears once the booked one arrives.
  - Pending transactions are shown read-only (greyed out). They can't be
    categorised and don't count in the budget.
- **Dedup key:** `transactionId`, falling back to `internalTransactionId`, then
  a hash of date, amount and description. Today transactions without a
  `transactionId` are silently skipped.
- **Sync window:** start from the latest transaction date minus 7 days, and
  let dedup absorb any overlap. Today's "since the latest date" misses
  transactions booked late.
- **Rules run on import** in priority order. The first match sets the
  category, the ratio and the transfer flag.
- **Rate limits:** GoCardless allows only a few calls per account per day. The
  UI shows the last sync time, and sync runs only when I ask.
- **Consent:** store each link's expiry date. Warn 7 days before it expires.
  Re-linking attaches the new link to the existing accounts using the IBAN or
  external ID.
- **Currency check:** accounts that aren't in DKK are refused at linking, with
  a clear message.

## 5. Architecture

```
app/                      FastAPI JSON API (Python)
  main.py                 app setup; in "prod" it also serves frontend/dist
  db.py, models.py        engine/session, and all SQLAlchemy models in one file
  bank/                   GoCardless client, linking, sync
  budget/                 calculations.py (pure), service.py, routes.py, schemas.py
  categories/  transactions/  rules/  reports/
frontend/                 React app (Vite + TypeScript + Tailwind)
  src/pages/              one file per screen
  src/components/         shared UI pieces
  src/api/                generated types and small fetch functions
```

- **Feature folders.** Each backend feature has `routes.py` (HTTP),
  `service.py` (logic plus database queries) and `schemas.py` (Pydantic). The
  repository layer goes away, and services use SQLAlchemy `select()` directly.
  That's one fewer place to look.
- **The domain doesn't know the UI.** `budget/calculations.py` imports nothing
  from FastAPI or SQLAlchemy. `REVIEW.md` will enforce this.
- **API:** REST under `/api`. Money is always sent as
  `{amount: <minor units>, currency: "DKK"}`. The frontend formats it with
  `Intl.NumberFormat` using that currency.
- **Ready for multi-currency later:**
  - Every account, transaction and line keeps its `currency`.
  - Nothing hardcodes `"DKK"` except one `BUDGET_CURRENCY` setting.
  - `calculations.py` takes amounts that are already in the budget currency.

  Adding multi-currency later then means adding a conversion step before the
  maths. The maths itself doesn't change.
- **Types flow from the backend.** FastAPI's OpenAPI schema generates the
  TypeScript types (`openapi-typescript`), so the frontend can't drift from
  the API.
- **Dev:** `uv run fastapi dev` plus `npm run dev` (Vite proxies `/api`).
  **Prod/local:** `npm run build`, then FastAPI serves everything with one
  command.

### Frontend choices (recommendations)

| Choice | Recommendation | Why |
|---|---|---|
| Language | **TypeScript** | Best practice. Your editor catches mistakes, and the API types are generated for you. |
| Setup | **Vite, single-page app** | react.dev recommends a framework for most apps, but the FastAPI backend already is our server. A Vite SPA is the documented "build from scratch" route and has the fewest moving parts. |
| Data fetching | **TanStack Query** | react.dev advises against hand-rolled fetching in Effects (race conditions, caching). This is the standard library for it. |
| Routing | **React Router** | Few pages; the most documented option. |
| Forms | Plain controlled inputs | No form library until we need one. |
| Styling | **Tailwind**, no component library | As agreed. Kept simple. |
| Tests | Vitest + Testing Library for logic-heavy components; Playwright for each slice's golden path | Most tests stay in pytest, where the maths is. |

## 6. Data changes

We start fresh (§7). The current `db/budget.db` and the two existing Alembic
migrations are replaced by a new schema with a single initial migration. After
that, every schema change gets its own migration as usual.

- **New:** `CategoryGroup`, `BudgetAssignment(month, category_id, amount)`,
  `TransactionLine(transaction_id, owner, category_id?, amount, currency)`,
  `PendingTransaction`, `Label`, `TransactionLabel`, `PayeeRule`, and a
  `settings` row (`budget_start_month`).
- **Changed:**
  - `Account` gets `my_share_default` (null for personal accounts),
    `starting_balance` and `roommate_starting_balance`.
  - `Transaction` gets `is_transfer`, `payee` and `source` (`bank`/`manual`),
    and loses `category_id` (it moves to lines).
  - `BankIntegration` gets `expires_at`.
- **Removed:** `User` and the `user_id` columns (single user, per intent).
  They come back with auth later.
- **Starting balances:** budgeting starts in the month you first use the app.
  - Each account's balance at the start of that month becomes the first
    month's Ready to Assign. It's calculated as the current balance minus the
    booked transactions since then.
  - For the shared account, only my share counts, and you enter the roommate's
    starting share once.
  - Earlier transactions stay visible as history but are not budgeted.

## 7. Decisions

| # | Question | Decision |
|---|---|---|
| D1 | Currency | DKK only for the MVP, and non-DKK accounts are refused at linking. The design stays ready for multi-currency (§5). |
| D2 | Existing data | Start fresh and re-sync. History is limited to what GoCardless returns. |
| D3 | Budget start month | The month I first use the app. Earlier transactions are visible history, not budgeted. |
| D4 | Pending transactions | Shown read-only, stored separately (§4). |
| D5 | Settling up with the roommate | Showing the roommate balance is enough for the MVP. |

## 8. Delivery slices

Each slice gets a `docs/plans/NN-*.md`, which you approve before any code is
written.

Because we start fresh (D2), the new database has no bank link. That's why
bank linking comes second: until then, slice 1 shows an empty transactions
list.

1. **API + React skeleton.**
   - New schema and a fresh database.
   - JSON routes in feature folders.
   - A Vite app with a transactions page, empty for now.
   - Jinja/HTMX removed, and `AGENTS.md` updated.
2. **Bank flow in React** (F4, F5, §4). Linking, sync, import fixes,
   pending transactions, the DKK check and consent renewal. After this slice,
   real transactions appear.
3. **Categories** (F1).
4. **Transaction lines and categorising** (F6, F7).
5. **Budget month** (F2, F3). This is where `calculations.py` comes in.
6. **Shared account and splits** (F8, F9).
7. **Payee rules** (F10).
8. **Labels and manual transactions** (F11, F12).
9. **Spending overview** (F13).
