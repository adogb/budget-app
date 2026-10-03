# Plan 02: Bank flow in React

Status: **approved** (2026-10-03).
Spec: [`spec.md`](../spec.md) F4, F5, §4, §8 slice 2.

## Goal

Slice 1 left a fresh database with no way to link a bank. After this slice I can,
from the React app:

1. link a bank (country → bank → log in at the bank → choose accounts);
2. sync my accounts when I ask, and see the last sync time;
3. see real transactions, with pending ones greyed out and kept apart;
4. see when bank consent expires, get a warning 7 days before, and renew it
   without losing any data.

The import also gets the fixes from spec §4 and the four follow-ups recorded at
the end of plan 01.

Two PRs again:
- **PR A, backend:** schema changes, import fixes, bank and sync routes. Testable
  through pytest and `/docs`.
- **PR B, frontend:** accounts page, linking pages, pending rows, first committed
  Playwright test.

## Scope

**In scope**
- Linking, renewal, sync, pending transactions, dedup, sync window, DKK check,
  consent expiry (spec §4, except "rules run on import", which is slice 7).
- `Transaction.payee` (from `creditorName`/`debtorName`). It's in spec §6 and only
  available at import time: rows imported without it can't be backfilled later,
  so it's cheapest to add now. Nothing uses it until slice 7.

**Out of scope**
- Categories, lines, rules, starting balances, `my_share_default` (slices 3–7).
- Automatic or scheduled sync (spec: sync only when I ask).
- Deleting a bank link or an account from the UI.

## How the GoCardless flow works (for reading the code)

```
Link page          API                         GoCardless / bank
──────────         ───                         ─────────────────
pick bank ───────► POST /api/bank/links ─────► create requisition
                   saves BankIntegration       (redirect = /link/callback,
                   (reference, not linked)      reference = our uuid)
          ◄─────── { link }
window.location = link ──────────────────────► I log in and consent
/link/callback?ref=<uuid> ◄──────────────────── bank redirects back
GET  /api/bank/links/{ref}/accounts ─────────► list the requisition's accounts
tick accounts, Save
POST /api/bank/links/{ref}/complete ─────────► details + balance per account
                   saves Accounts, linked_at, expires_at
→ /accounts
```

Renewal is the same flow started from an existing link's "Renew" button, which
skips the bank picker. On completion the accounts are matched to the ones I
already have, so their transactions stay.

## PR A: Backend

### Schema changes (`app/models.py`, one migration)

| Table | Change | Why |
|---|---|---|
| `bank_integrations` | + `reference` (uuid, unique) | GoCardless sends it back as `?ref=` on the callback, so we know which link it is |
| | + `linked_at` (nullable, UTC) | Null = started but not completed. Makes "setup done" explicit instead of inferring it from `Account` rows |
| | + `expires_at` (nullable, UTC) | Consent expiry (F5) |
| | `requisition_id` stays | |
| `accounts` | + `bank_integration_id` (FK, nullable) | Which link an account belongs to, for renewal and the expiry warning |
| | + `last_synced_at` (nullable, UTC) | Shown in the UI (spec §4 rate limits) |
| `transactions` | + `import_key` + unique `(account_id, import_key)` | The dedup key (below), enforced by the database |
| | + `payee` (nullable) | See scope |
| `pending_transactions` (new) | `account_id`, `amount_minor`, `currency`, `description`, `payee`, `booking_date` (nullable), `value_date` | Spec §4 / D4 |

- Turn on `render_as_batch=True` in `alembic/env.py`: SQLite can't add a unique
  constraint to an existing table without it.
- The migration backfills `import_key` for any existing rows from
  `bank_transaction_id`, else `gc_transaction_id`, else `id`, so it runs on a
  non-empty database too.
- `expires_at = linked_at + 90 days`. We use GoCardless's default agreement
  (90 days of access) and consent is given minutes before `complete`, so this is
  accurate to within minutes without an extra API call.

### Import fixes (`app/bank/sync.py`)

| Fix | How |
|---|---|
| Pending kept separate | Only `booked` goes into `transactions`. `pending` replaces that account's `pending_transactions` rows on every sync (delete + insert, one commit) |
| Dedup key | `transactionId` → `internalTransactionId` → sha256 of `date|amount|description|n`, where `n` counts identical rows on that day in the response. Without `n`, two identical coffees on the same day would collapse into one. `n` is stable because the sync window always covers whole days |
| Duplicates within one response | Keys are collected in a `set` while building the batch, so a repeated `transactionId` is inserted once |
| No more silent skipping | Rows without `transactionId` now get a key instead of being dropped |
| Sync window | `latest booking_date − 7 days`; first sync 90 days back. Dedup absorbs the overlap |
| Empty `remittanceInformationUnstructuredArray` | `_description()` takes the first non-empty of array item, unstructured, additional info, payee, else `"No description"` |
| Pending date fallback | Gone: pending rows keep `booking_date = None` and never move the sync window |
| API errors | `requests.RequestException` from every client call becomes `BankAPIError`, with GoCardless's `summary`/`detail` in the message |
| `last_synced_at` | Set at the end of a successful sync |

### Linking and renewal (`app/bank/linking.py`)

- `start_link(db, client, institution_id, country_code, redirect_url)`: deletes
  any *unlinked* integrations (abandoned attempts), creates the requisition with
  a new `reference`, saves the integration, returns the bank's `link`.
- `list_link_accounts(db, client, reference)` → per account: `external_id`,
  `name`, `iban`, `currency`, `eligible` (currency == `BUDGET_CURRENCY`) and
  `already_linked` (matches an existing account, used to pre-tick on renewal).
- `complete_link(db, client, reference, external_ids)`:
  - refuses any non-DKK account with a 400 and a clear message (spec D1);
  - matches each to an existing `Account` by `external_id`, then by `iban`.
    A match is updated (new `external_id`, `bank_integration_id`, balance); no
    match creates a new account. Transactions are never touched;
  - sets `linked_at` and `expires_at`;
  - deletes old integrations left with no accounts (the one that was renewed).
- `consent_status(expires_at, now)` → `"ok" | "expiring" | "expired"`, a pure
  function (expiring = 7 days or fewer left).
- The blind `except Exception` in `complete_setup` goes: one failing account now
  fails the request with a `BankAPIError`, since a half-linked bank is worse
  than a clear error I can retry.

### Routes

| Route | Feature folder | Does |
|---|---|---|
| `GET /api/bank/countries` | `bank/routes.py` | The supported list (DK first) |
| `GET /api/bank/institutions?country=DK` | | Banks in a country |
| `POST /api/bank/links` `{institution_id, country_code, redirect_url}` | | `start_link` → `{link}` |
| `GET /api/bank/links/{reference}/accounts` | | `list_link_accounts` |
| `POST /api/bank/links/{reference}/complete` `{external_ids}` | | `complete_link` → `204` |
| `GET /api/bank/links` | | Linked integrations: bank name, `expires_at`, `consent_status`, account ids. Drives the warning and "Renew" |
| `POST /api/bank/sync` | | Syncs every account whose consent isn't expired. Returns one result per account: new count, or the error. One failing account doesn't stop the others |
| `GET /api/transactions/pending` | `transactions/` | Pending rows, newest first |

- `AccountOut` gains `last_synced_at` and `bank_integration_id`;
  `TransactionOut` gains `payee`.
- `redirect_url` comes from the frontend (`window.location.origin +
  "/link/callback"`), so the same code works on :5173 in dev and :8000 in prod.
- The `BankAPIError` → `502 {detail}` handler goes back into `main.py`
  (plan 01 follow-up).
- The client comes in through a `get_bank_client` dependency, so tests swap in a
  `Mock` with `app.dependency_overrides`, like `get_db`.

### Order of work (one commit each)

1. Models + migration (`render_as_batch`, backfill) + `alembic check`.
2. Sync: dedup key, batch dedup, description fix, window, error translation.
3. Pending table in sync.
4. Linking: `start_link`, `list_link_accounts`, `complete_link`, renewal
   matching, DKK check, `consent_status`.
5. `bank/routes.py`, `schemas.py`, the client dependency, the 502 handler.
6. Pending route and the new fields on `AccountOut`/`TransactionOut`.
7. `npm run gen:api` (types for PR B).

### Tests that prove it

All with a mocked client; nothing calls GoCardless.

| Test | Proves |
|---|---|
| `test_sync::test_booked_only_into_transactions` | Pending rows land in `pending_transactions`, not `transactions` |
| `test_sync::test_pending_replaced_each_sync` | A pending row that's now booked disappears from pending |
| `test_sync::test_dedup_falls_back_to_internal_id_then_hash` | All three key sources work; resyncing the same response adds 0 |
| `test_sync::test_identical_rows_same_day_both_kept` | Two identical coffees stay two rows, and a resync adds none |
| `test_sync::test_duplicate_id_in_one_response` | Inserted once |
| `test_sync::test_window_starts_7_days_before_latest` | `date_from` passed to the client |
| `test_sync::test_empty_remittance_array` | No `IndexError`; description falls back |
| `test_sync::test_client_error_becomes_bank_api_error` | |
| `test_linking::test_complete_creates_accounts_and_sets_expiry` | `linked_at`, `expires_at = +90 days` |
| `test_linking::test_non_dkk_refused` | 400, nothing saved |
| `test_linking::test_renewal_matches_by_iban_keeps_transactions` | New `external_id`, same account id, transactions intact, old integration gone |
| `test_linking::test_start_deletes_only_unlinked_integrations` | |
| `test_linking::test_consent_status` | ok / expiring at 7 days / expired |
| `test_bank_api::test_sync_reports_per_account_errors` | One failing account, the other still syncs |
| `test_bank_api::test_bank_error_is_502` | |
| `test_transactions_api::test_pending_listed_separately` | |

The existing 15 bank tests are adapted where behaviour changes on purpose
(window, pending, skipped rows), and each changed assertion is called out in the PR.

## PR B: Frontend

### Pages and routes

```
frontend/src/
  App.tsx                 + "Accounts" nav link, routes below
  api/client.ts           + postJson(); errors show the API's `detail`
  api/accounts.ts         fetchAccounts()
  api/bank.ts             countries, institutions, links, startLink,
                          linkAccounts, completeLink, syncAll
  pages/AccountsPage.tsx  accounts grouped by bank link: balance, last synced,
                          consent badge, "Renew"; "Sync" and "Link a bank" buttons
  pages/LinkBankPage.tsx  /link: country select (DK default) + bank search list;
                          clicking a bank goes to the bank's login page
  pages/LinkCallbackPage.tsx  /link/callback?ref=: account checkboxes, non-DKK
                          ones disabled with the reason, renewed ones pre-ticked
  pages/TransactionsPage.tsx  + pending rows on top, greyed, tagged "Pending",
                          + payee column
  components/ConsentBadge.tsx  "Expires in 5 days" (amber) / "Expired" (red)
```

- An expiring or expired link also shows a banner on the Transactions page, so I
  see it without opening Accounts.
- After a sync, the page shows "Imported 12 new transactions" (or each account's
  error), and the accounts, transactions and pending queries are refetched.
- If the callback has no accounts (I cancelled at the bank), the page says so and
  links back to `/link`.

### Order of work

1. `postJson` + error detail, `api/accounts.ts`, `api/bank.ts`.
2. AccountsPage (read-only), nav, routes.
3. LinkBankPage, then LinkCallbackPage.
4. Sync button with result message.
5. ConsentBadge, Renew, the Transactions banner.
6. Pending rows and payee on TransactionsPage.
7. Playwright setup and the golden-path test.

### Tests that prove it

| Check | Proves |
|---|---|
| `e2e/link-and-sync.spec.ts` (Playwright, `/api` mocked with `page.route`) | Link page → pick bank → (callback visited directly) → tick an account, DKK-only enforced → Accounts shows it → Sync → message, transactions and greyed pending rows appear |
| `npm run build`, `npm run lint` | Types compile against the regenerated schema |
| Real-bank check (you, once) | Link my real bank, sync, renew. GoCardless can't be faked end to end, and its rate limits mean I shouldn't run this repeatedly. Screenshots in the PR |

Adds `@playwright/test` as a dev dependency and `npm run e2e`.

### React concepts in this PR

| Concept | Where you'll see it |
|---|---|
| [State: a component's memory](https://react.dev/learn/state-a-components-memory) | Selected country, search text, ticked accounts |
| [Responding to events](https://react.dev/learn/responding-to-events) | Sync, Save, clicking a bank |
| [Reacting to input with state](https://react.dev/learn/reacting-to-input-with-state) | The callback page's idle / saving / error states |
| [Controlled inputs](https://react.dev/reference/react-dom/components/input#controlling-an-input-with-a-state-variable) | Search box, country select, checkboxes |
| [Updating arrays in state](https://react.dev/learn/updating-arrays-in-state) | Ticking/unticking accounts without mutating the array |
| [Choosing the state structure](https://react.dev/learn/choosing-the-state-structure#avoid-redundant-state) | The filtered bank list is computed during render, not stored |
| [Sharing state between components](https://react.dev/learn/sharing-state-between-components) | AccountsPage owns the sync result shown below the button |
| [You might not need an Effect](https://react.dev/learn/you-might-not-need-an-effect#sending-a-post-request) | Saving runs in the click handler, not in an Effect |

**Outside React:**
- [TanStack Query mutations](https://tanstack.com/query/latest/docs/framework/react/guides/mutations) and [invalidation](https://tanstack.com/query/latest/docs/framework/react/guides/invalidations-from-mutations): `useMutation` for sync and save, then refetch
- [React Router `useSearchParams`](https://reactrouter.com/api/hooks/useSearchParams): reading `?ref=` on the callback
- [Playwright mocking](https://playwright.dev/docs/mock): faking `/api` in the e2e test

## How to review

- **PR A:** `app/models.py` + the migration → `app/bank/sync.py` (compare with the
  fixes table) → `app/bank/linking.py` → `app/bank/routes.py`. The new tests read
  as a list of behaviours.
- **PR B:** `App.tsx` → `AccountsPage` → `LinkBankPage` → `LinkCallbackPage` →
  the e2e test, with the concepts table open.

## Risks

- **Rate limits:** ~4 calls per account per day per endpoint. Linking uses
  details + balances; each sync uses transactions + balances. Don't test against
  the real bank more than a couple of times a day.
- **Renewal matching relies on IBAN.** If my bank returns no IBAN and changes
  `external_id`, a renewed account would come in as a new account. The PR
  description will say how to check this, and we'll handle it if it happens.
- **Same-day identical rows without any bank ID** are kept apart by the occurrence
  counter. If the bank reorders or drops one between syncs, a duplicate could
  appear. Unlikely for booked transactions, and visible if it happens.
