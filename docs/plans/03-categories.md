# Plan 03: Categories

Status: **approved** (2026-10-18).
Spec: [`spec.md`](../spec.md) F1, §1, §5, §6, §8 slice 3.

## Goal

After this slice I can build my own category tree:

1. create, rename and reorder **category groups**, and the **categories** in
   them;
2. **hide** a group or a category without losing it;
3. mark one group as the **income** group;
4. see the whole tree on a new Categories page, in my own order;
5. start from the category list I already made, in `docs/Categories.xlsx`,
   instead of an empty page.

Nothing is assigned to a transaction yet, and no budget maths runs yet. F1 is
about the tree; the picker (slice 4) and the budget month (slice 5) consume it.

Two PRs again:

- **PR A, backend:** two new tables, one migration, `app/categories/`, the
  routes, and the starter tree with its one-shot seed script. Testable through
  pytest and `/docs`.
- **PR B, frontend:** the Categories page, the inline editing, and a Playwright
  test for the golden path.

## Scope

**In scope**
- `CategoryGroup` and `Category` come back (they were removed in slice 1).
- Create, rename, reorder, hide; one income group.
- `GET /api/category-groups` returning the whole tree in one response.
- The **starter tree** derived from `docs/Categories.xlsx`: 14 groups, 68
  categories, and the one-shot script that loads it (C5, C7).

**Out of scope**
- Assigning a category to anything: transaction lines are slice 4.
- `BudgetAssignment`, Ready to Assign, income in the maths: slice 5. This slice
  only records *which* group is income.
- Deleting a group or category (see decision C1).
- Moving a category to another group, drag-and-drop, colours and icons.
- The `Internal transfers` row (C5) and the savings/investments split.
- Reading the workbook at runtime, and any "load starter categories" button in
  the UI.

## Decisions

| # | Decision | Why |
|---|---|---|
| C1 | **Hide, don't delete.** No `DELETE` routes. | F1 asks for "create, rename, reorder and hide", and slice 4 will point transaction lines at categories. A hidden row keeps those pointers valid; the hidden flag is the archive. |
| C2 | **Order is an integer, replaced wholesale.** `PUT .../order` takes the full list of ids in its new order. | Two "move up" buttons plus an atomic list replace is simpler and race-free compared with sending two `sort_order` patches. It also fits drag-and-drop later without an API change. |
| C3 | **At most one income group** (`is_income`), and it can't be hidden. | §1 says "one kind of group holds income categories". Ready to Assign (slice 5) needs exactly one income bucket, and a hidden income group would quietly change the maths. |
| C4 | **Names are unique:** group names against each other, category names within their group. | A duplicated "Groceries" in one group is a footgun in the slice 4 picker. Costs one constraint and one clear 400. Renaming into a clash is refused with the API's message. |
| C5 | **Start from my own list**, not from defaults: `docs/Categories.xlsx`, reshaped once into a committed starter tree (below). `Internal transfers` (Type `Internal`) is the only row **not** seeded. | The sheet is how I already think about my spending, so there is nothing to invent. It needs one reshaping pass because our model always puts a category in a group while the sheet has four rows with no folder, and because two groups hold categories that belong with another group. `Internal transfers` isn't a category: §2 gives a transfer no category and no budget effect, so it becomes `Transaction.is_transfer` in slices 6–7. |
| C6 | `is_income` is a **boolean, not a `kind` enum**. | One boolean is enough for the one kind §1 names, and it's the cheapest change while the table is new. Slice 5 reads it for `income(m)`. |
| C7 | The starter tree is loaded by a **one-shot script** (`uv run python -m scripts.seed_categories`), from a committed JSON file, and not by a migration. | Migrations are for schema; a data seed there would run on every fresh database, including the ones tests make, and would be awkward to reverse. The script is explicit, re-runnable with `--replace`, and keeps the starter tree out of the migration history. |

## The starter tree (C5)

`docs/Categories.xlsx` is a flat table: `ID, Level, Parent ID, Category,
Description, Type`. `Level 0` is a group, `Level 1` a category under it, and
`Description` is empty on every row, so no text is carried over.

| From the sheet | Becomes |
|---|---|
| `Level 0` expense row that has children (12 of them) | a group |
| its `Level 1` rows (58 in total) | its categories, in sheet order |
| the 6 `Type = Income` rows | the categories of one `Income` group, placed first |
| 4 top-level rows with no children | folded in, see below |
| `Internal transfers` (`Type = Internal`) | nothing: it is the transfer flag, not a category |

### What changes from the sheet

| # | Change | Why |
|---|---|---|
| R1 | `Groceries` joins **Food and drinks**, first in the group | The sheet's split between it and the cafe rows is about *where* the food came from, not which envelope pays. The alternative — a `Groceries` group holding one category also called `Groceries` — is a redundant heading on the budget screen. |
| R2 | New group **Other** takes `Cash withdrawal / deposit`, `Other expense`, `Unknown expense` | They are the rows with no folder, and every "Other …" in the sheet already lives inside a group. Cash withdrawals are really money leaving the bank before I decide what it was, so `Other` is where it does least harm. |
| R3 | `Realkredit loan` and `Bank loan` move from **Home and utilities** to **Loans** | `Loans` already holds `Consumer loans`, `Car leasing`, `Overdraft` and `Other loans`; two more loans under Home looked like an accident. Home keeps only running costs. |
| R4 | `Phone & internet` and `TV services` move from **Entertainment, IT and learning** to **Home and utilities**, which becomes **Home, bills and utilities** | Both are recurring bills like electricity, and it thins out a 7-category group. |

So the starter tree is **14 groups and 68 categories**: `Income` first, then the
sheet's group order with `Other` last, each group's categories in sheet order
except where R1–R4 say otherwise. Groups in order, with their category counts:

```
Income (6, income) · Food and drinks (5) · Transportation (4) · Travel (6) ·
Loans (6) · Savings and investments (6) · Administration (3) ·
Nonprofit Organisations (2) · Home, bills and utilities (8) ·
Personal and Healthcare (2) · Entertainment, IT and learning (5) ·
Medical and safety (7) · Shopping (5) · Other (3)
```

The sheet also settles C4 for us: `Food and drinks` appears twice — once as a
group (`ID 3`), once as a category under `Travel` (`ID 78`). Unique *within a
group* allows that; unique overall would not.

`docs/Categories.xlsx` stays the document of record, and nothing reads it at
runtime, so no spreadsheet library becomes a dependency. The checked-in JSON is
generated from it once, with R1–R4 applied, and is what the seed loads:

```json
[
  {"name": "Income", "is_income": true,
   "categories": ["Salary", "Investment income",
                  "Interest received (excl. loans)",
                  "Social security, unemployment benefits",
                  "Other income", "Unknown income"]},
  {"name": "Food and drinks",
   "categories": ["Groceries", "Cafes, restaurants, bars",
                  "Snacks, bakery, food on the go",
                  "Take away", "Other food and drinks"]},
  {"name": "Other",
   "categories": ["Cash withdrawal / deposit", "Other expense",
                  "Unknown expense"]}
]
```

## Schema (`app/models.py`, one migration)

```
category_groups
  id           int, pk
  name         str(80), unique, not null
  is_income    bool, not null, default false
  hidden       bool, not null, default false
  sort_order   int,  not null, default 0

categories
  id           int, pk
  group_id     int, fk -> category_groups.id, not null
  name         str(80), not null
  hidden       bool, not null, default false
  sort_order   int,  not null, default 0
  unique (group_id, name)
```

- `CategoryGroup.categories` is a relationship ordered by `sort_order`, `id`, so
  a tie can't shuffle the tree between requests.
- Both tables are new, so the migration is pure `create_table`: no backfill.
  `render_as_batch` is already on in `alembic/env.py` (plan 02).
- No timestamps: the explicit `sort_order` is the only ordering that matters
  here, and nothing displays "last edited".
- `sort_order` isn't unique; the order endpoint rewrites it to `0..n-1`.

## PR A: Backend

### `app/categories/`

```
app/categories/
  routes.py      groups_router and categories_router (HTTP)
  service.py     the queries and the rules (plain functions)
  schemas.py     CategoryGroupOut, CategoryOut, GroupIn, GroupPatch,
                 CategoryIn, CategoryPatch, OrderIn
  errors.py      CategoryError (400), CategoryNotFoundError (404)
  seed.py        the starter tree: load, validate, apply
  starter.json   the 14 groups and 68 categories from docs/Categories.xlsx,
                 with the R1–R4 changes applied
scripts/
  seed_categories.py   the one-shot CLI around app/categories/seed.py
```

Services take a session and return models, as in `accounts/` and
`transactions/`:

| Function | Does |
|---|---|
| `list_groups(db)` | Every group in order, categories eager-loaded and in order |
| `create_group(db, name, is_income)` | Validates the name and C3, then inserts |
| `update_group(db, group_id, *, name, hidden, is_income)` | Only the fields given; 404 if unknown |
| `reorder_groups(db, ids)` | Checks `ids` is exactly every group, then rewrites `sort_order` |
| `create_category(db, group_id, name)` | Group must exist; name unique in it |
| `update_category(db, category_id, *, name, hidden)` | As `update_group` |
| `reorder_categories(db, group_id, ids)` | `ids` must be exactly that group's categories |

Validation split:

- **Pydantic:** the types only.
- **Service:** the name rules (trimmed, non-empty, at most 80 characters),
  uniqueness (C4) and the income rules (C3). They raise `CategoryError`, which
  `main.py` turns into a 400 carrying the message I want to read.

  The name rules live in the service rather than in Pydantic: a schema-level
  failure is FastAPI's own 422, whose `detail` is a list of error objects, and
  `client.ts` can only show a string. Keeping every refusal a 400 with a string
  `detail` means the page shows all of them the same way.

`reorder_*` treats the sent list as the whole truth: unknown ids, missing ids,
or a category from another group is a 400 and nothing is written.

### The seed (C5, C7)

- `starter.json` is read into a small Pydantic model (`StarterGroup`: `name`,
  `is_income`, `categories: list[str]`), so a malformed or duplicated file fails
  loudly at load time rather than half-loading a tree.
- It validates what the database will enforce anyway — unique group names,
  unique category names within a group, at most one income group (C3) — and then
  writes the whole tree in **one commit**, so a bad file can't leave half a
  tree behind.
- `sort_order` comes from list position: groups `0..13`, each group's categories
  from `0`. `Income` is first, because it is first in the file.
- Applying it to a database that already has groups is refused with a clear
  message; `--replace` deletes the existing groups and categories first (a
  script may do what the API deliberately can't — C1).
- The CLI is thin, like `scripts/export_openapi.py`:
  ```
  uv run python -m scripts.seed_categories           # refuses if not empty
  uv run python -m scripts.seed_categories --replace # clear, then load
  ```
  It prints what it did: `Added 14 groups and 68 categories.`
- `AGENTS.md` gains the command, next to the other `uv run` ones.

### Routes

Two routers in one feature folder, both included in `main.py`:

| Route | Does |
|---|---|
| `GET /api/category-groups` | The tree: groups in order, each with its categories in order. Hidden rows included |
| `POST /api/category-groups` `{name, is_income?}` | `201` the new group |
| `PATCH /api/category-groups/{id}` `{name?, hidden?, is_income?}` | `200` the group |
| `PUT /api/category-groups/order` `{ids}` | `204` |
| `POST /api/categories` `{group_id, name}` | `201` the new category |
| `PATCH /api/categories/{id}` `{name?, hidden?}` | `200` the category |
| `PUT /api/category-groups/{group_id}/categories/order` `{ids}` | `204` |

- One `GET` returns everything: the data is tens of rows, so the page never
  needs a second request, and the tree arrives already in my order.
- Hidden rows stay in the response with `hidden: true`; the page decides what to
  show. Filtering here would make "show hidden" a second round trip.
- `main.py` gains `ERROR_STATUS[CategoryError] = 400` and
  `ERROR_STATUS[CategoryNotFoundError] = 404`, next to the bank entries, so the
  errors use the same `{detail}` shape the frontend already reads.
- `CategoryOut` carries `sort_order` too, so the API shows the order it is
  sending rather than leaving it implied by array position.

### Order of work (one commit each)

1. `app/models.py` + `uv run alembic revision --autogenerate -m "categories"`
   + `upgrade head` + `alembic check`.
2. `errors.py`, then `service.py`: create/update with validation, then the two
   reorder functions. Unit-testable before any HTTP exists.
3. `schemas.py`, `routes.py`, the two `ERROR_STATUS` entries in `main.py`.
4. `starter.json`, `seed.py`, `scripts/seed_categories.py`, and the `AGENTS.md`
   line. Run it against the real database and eyeball the tree in `/docs`.
5. `tests/test_categories_api.py` and `tests/test_seed.py`.
6. `npm run gen:api`, so PR B has its types.

### Tests that prove it

| Test | Proves |
|---|---|
| `test_categories_api::test_empty_tree` | `GET /api/category-groups` → `200 []` on a fresh database |
| `test_categories_api::test_create_group_and_category` | `201`, the ids come back, the category appears inside its group |
| `test_categories_api::test_tree_is_ordered` | Groups and the categories in them follow `sort_order`, not insertion order |
| `test_categories_api::test_rename_and_hide` | `PATCH` round-trips name and hidden; a hidden group is still in the tree |
| `test_categories_api::test_duplicate_group_name_is_400` | C4, with the name in `detail` |
| `test_categories_api::test_duplicate_category_name_in_same_group_is_400` | C4; the same name in *another* group is fine |
| `test_categories_api::test_only_one_income_group` | Second one is 400; moving `is_income` from one group to another works |
| `test_categories_api::test_income_group_cannot_be_hidden` | C3 |
| `test_categories_api::test_blank_name_is_400` | `""` and `"   "` |
| `test_categories_api::test_reorder_groups` | The new order comes back and `sort_order` is `0..n-1` |
| `test_categories_api::test_reorder_rejects_a_partial_list` | 400 and the order is unchanged |
| `test_categories_api::test_reorder_categories_is_scoped_to_the_group` | An id from another group is 400 |
| `test_categories_api::test_patch_unknown_id_is_404` | `CategoryNotFoundError` |

`tests/test_seed.py` proves the starter tree itself:

| Test | Proves |
|---|---|
| `test_seed::test_loads_the_starter_tree` | 14 groups and 68 categories; `Income` is first, is the income group, and holds the 6 income categories |
| `test_seed::test_order_follows_the_file` | `sort_order` is `0..n-1` at both levels, in file order |
| `test_seed::test_the_reorg_is_applied` | `Groceries` is in Food and drinks; `Other` holds the three leftovers; `Loans` has the two home loans; `Home, bills and utilities` has the two TV/phone rows and no loans |
| `test_seed::test_refuses_a_non_empty_database` | A second run changes nothing and says why |
| `test_seed::test_replace_starts_over` | `--replace` leaves one tree, not two |
| `test_seed::test_food_and_drinks_twice_is_fine` | The sheet's `Food and drinks` group and `Travel`'s category coexist (C4) |
| `test_seed::test_a_second_income_group_is_refused_before_writing` | A bad file leaves the database empty, not half-loaded |

The seed tests use the in-memory fixture, so they never look at
`db/budget.db`.

On top of that: `uv run ruff check`, `uv run ruff format --check`,
`uv run pyright`, and `alembic check` against the migrated database.

## PR B: Frontend

### Files

```
frontend/src/
  App.tsx                      + "Categories" nav link and /categories route
  api/categories.ts            CategoryGroup / Category types,
                               fetchCategoryGroups, createGroup, updateGroup,
                               reorderGroups, createCategory, updateCategory,
                               reorderCategories
  pages/CategoriesPage.tsx     the tree: add, rename, hide, move
  components/EditableName.tsx  the name, or an input while renaming
  lib/reorder.ts               move(items, index, direction) + reorder.test.ts
```

### Page

- A card per group: name, an "Income" badge when `is_income`, its categories,
  then an "Add category" input.
- "Add group" at the top. Empty state: "No groups yet. Add one like 'Housing'."
- Each group and category has rename, hide and up/down.
- A "Show hidden" toggle; hidden rows are greyed and marked "Hidden".
- Every action is a `useMutation` that invalidates `['category-groups']` — the
  same pattern as the slice 2 sync button, so the tree always comes back from
  the server in its stored order.
- Errors show the API's `detail` (already how `client.ts` works), which is what
  the uniqueness and income messages need.

### Order of work

1. `lib/reorder.ts` with its test: `move(['a','b','c'], 2, 'up')` →
   `['a','c','b']`; moving past either end returns the list unchanged.
2. `api/categories.ts`.
3. `CategoriesPage` read-only: the cards, order and badges.
4. Add group / add category, then rename via `EditableName`.
5. Hide, "Show hidden", up/down wired to the two order endpoints.
6. `npm run gen:api` types check with `npm run build`, `npm run lint`, then the
   Playwright test.

### Tests that prove it

| Check | Proves |
|---|---|
| `reorder.test.ts` (Vitest) | Moving up, moving down, and no-op at the ends without mutating the input array |
| `e2e/categories.e2e.ts` (Playwright, `/api` mocked) | Add a group → add two categories → rename one → hide it → move one up; each step shows in the tree, and the reorder request carries the new order |
| `npm run build`, `npm run lint` | Types compile against the regenerated schema |

The Playwright test fakes `**/api/category-groups` and its children with one
handler per pattern that switches on `route.request().method()`, like the slice
2 test does for `/api/bank/links`.

### React concepts in this PR

| Concept | Where you'll see it |
|---|---|
| [State: a component's memory](https://react.dev/learn/state-a-components-memory) | The "new group" text and the "Show hidden" toggle |
| [Reacting to input with state](https://react.dev/learn/reacting-to-input-with-state) | A row is either showing a name or an input; one `editingId` decides which |
| [Choosing the state structure](https://react.dev/learn/choosing-the-state-structure#avoid-redundant-state) | The tree itself is TanStack Query's, not state; only `editingId` and the draft text are |
| [Controlled inputs](https://react.dev/reference/react-dom/components/input#controlling-an-input-with-a-state-variable) | The rename input and the two "add" inputs |
| [Responding to events](https://react.dev/learn/responding-to-events) | Enter saves, Escape cancels, the arrows move a row |
| [Sharing state between components](https://react.dev/learn/sharing-state-between-components) | `CategoriesPage` owns which row is being renamed; `EditableName` gets it as props |
| [Rendering lists](https://react.dev/learn/rendering-lists) | `groups.map(...)` then `categories.map(...)`, and why each needs a key |
| [Conditional rendering](https://react.dev/learn/conditional-rendering) | Hidden rows, the income badge, input vs name |

**Outside React:**
- [TanStack Query mutations](https://tanstack.com/query/latest/docs/framework/react/guides/mutations)
  and [invalidation](https://tanstack.com/query/latest/docs/framework/react/guides/invalidations-from-mutations):
  one mutation per action, then refetch the tree.

## How to review

- **PR A:** read in this order:
  1. `app/models.py` (the two tables and the two constraints)
  2. the migration, checking it is only `create_table`
  3. `app/categories/service.py` — the validation and the `sort_order` rewrite
     are the whole slice
  4. `app/categories/seed.py` with `starter.json` open beside it: check that
     R1–R4 are the only differences from `docs/Categories.xlsx`
  5. `app/categories/routes.py` and the two `main.py` lines
  6. `tests/test_categories_api.py` and `tests/test_seed.py`, which read as the
     list of rules

  The order tests and the two "rejects" tests are the ones worth reading
  closely.
- **PR B:** read in this order:
  1. `api/categories.ts`
  2. `CategoriesPage.tsx`
  3. `EditableName.tsx`
  4. `e2e/categories.e2e.ts`

  Keep the React concepts table open alongside.

## Risks

- **Whole-list reorder is last-write-wins.** Two tabs reordering at once would
  clobber each other. One user, and the list is short; not worth optimistic
  locking now.
- **No delete means no way to un-create.** A mistyped group is renamed or
  hidden. If the hidden pile gets noisy, deleting arrives with slice 4, where
  the line references it has to respect are designed anyway.
- **Uniqueness makes rename fallible.** The rename input can come back with a
  400; the page shows the message and keeps the input open.
- **`is_income` earns its keep in slice 5, not here.** It is one boolean and one
  rule, added while the table is new, so slice 5 doesn't migrate the table the
  user has just filled in.
- **The starter tree is sticky.** With no delete and no move (C1), anything the
  reorg gets wrong has to be renamed or hidden by hand, so it is worth reading
  R1–R4 above carefully now. `--replace` re-seeds while the tree is still
  settling, but anything created on the page in the meantime goes with it.
- **The sheet and the JSON can drift.** The JSON carries R1–R4, so it is no
  longer a straight copy of `docs/Categories.xlsx`; editing the sheet afterwards
  changes nothing until someone rewrites the JSON by hand. If the sheet turns
  out to be the place I keep editing, that is the moment to add a real importer
  — not before.
