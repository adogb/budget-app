# Intent

Status: **accepted** (2026-09-26).

## Problem

I want to budget my money the envelope way: every krone I have gets a job, and
leftovers roll over. I don't want to type in bank transactions by hand. The
existing apps don't quite fit:

- **Actual Budget** and **Firefly III** do more than I need, so they're harder
  to understand and shape to my life.
- Their categories don't match how I think about my spending.

So I'm building a small app that I can fully understand, with categories that
fit my lifestyle and transactions imported from my bank.

## Who and where

- **One user: me.** No logins for the MVP.
- **Runs on my laptop** for now. It may be self-hosted later, and that's when
  auth comes in.
- **A shared account with my roommate** for groceries and housing. It sits at
  the same bank as my own accounts and is linked with my login. I want my share
  of each shared purchase to count in my own budget.

## What I want

1. **Envelope budgeting like Actual Budget.** I only budget money I actually
   have, there's a "Ready to Assign" amount, leftovers roll over, and
   overspending is covered from the next month.
2. **Automatic import** of transactions and balances from my bank
   (GoCardless Bank Account Data).
3. **Flexible categories:** my own groups and categories, payee rules that
   categorise automatically, splitting one transaction over several
   categories, and free-form labels (e.g. `holiday-2026`).
4. **Shared purchases split with my roommate:** a default ratio, which I can
   override per category or per transaction. Only my share hits my envelopes.
5. **Quick categorising:** a month of transactions in minutes, not an evening.
6. **Spending overview:** where my money went over the last months.

## Constraints

- **Stack:** a Python/FastAPI JSON API with SQLite, and a React frontend styled
  with Tailwind CSS, kept simple. The budgeting logic must not depend on the UI.
- **Easy to follow:** I'm not a frontend developer, and I want to be able to
  navigate the code and follow what it does. When in doubt, choose simplicity
  over features, unless it's best practice.
- **Learning React as we go:** plans link to the React docs for each concept
  they use, so I can read up on what's being built.
- **Bank data:** GoCardless Bank Account Data. It works today; bank consent has
  to be renewed every 90 days.
- **Personal learning project:** Claude implements, and I review and approve
  every stage.

## Non-goals (MVP)

- Multiple users and authentication
- A mobile app (the browser is enough)
- Investments, pensions, loans and net worth

## Done means

- I do my monthly budget in this app instead of anything else.
- I never type a bank transaction by hand.
- Categorising a month takes minutes.
- I can see my spending per category over past months.

## Open questions (to settle in `spec.md`)

- **Transfers:** How are my transfers into the shared account treated? As an
  internal transfer, since my share is counted per purchase? And the roommate's
  contributions should not count as my income.
- **Currency:** Is DKK only enough, or is multi-currency needed?
- **Frontend tooling:** TypeScript or JavaScript? Plain `fetch` or a data
  library? Which router? Keep the list of dependencies short.
- **Bank fallback:** If GoCardless access ever stops, is CSV import the fallback?
