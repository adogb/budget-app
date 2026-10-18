import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import {
  type Category,
  type CategoryGroup,
  createCategory,
  createGroup,
  fetchCategoryGroups,
  reorderCategories,
  reorderGroups,
  updateCategory,
  updateGroup,
} from '../api/categories'
import EditableName from '../components/EditableName.tsx'
import { type Direction, move } from '../lib/reorder'

// What a row can ask the page to do. The page owns the mutations, so the rows
// stay presentational.
type Actions = {
  renameGroup: (id: number, name: string) => void
  hideGroup: (id: number, hidden: boolean) => void
  moveGroup: (ids: number[]) => void
  addCategory: (groupId: number, name: string) => void
  renameCategory: (id: number, name: string) => void
  hideCategory: (id: number, hidden: boolean) => void
  moveCategory: (groupId: number, ids: number[]) => void
}

export default function CategoriesPage() {
  // Hidden rows keep their place in the tree and are only left out of the
  // render, so the toggle changes nothing about the stored order (plan 03 C1).
  const [showHidden, setShowHidden] = useState(false)

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Categories</h1>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={showHidden}
            onChange={(event) => setShowHidden(event.target.checked)}
          />
          Show hidden
        </label>
      </div>
      <CategoriesContent showHidden={showHidden} />
    </section>
  )
}

function CategoriesContent({ showHidden }: { showHidden: boolean }) {
  const queryClient = useQueryClient()
  const groups = useQuery({ queryKey: ['category-groups'], queryFn: fetchCategoryGroups })

  // Every change goes through one of these, and each one refetches the tree, so
  // names and order always come back from the server (plan 03 C2).
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['category-groups'] })
  const addGroup = useMutation({
    mutationFn: (name: string) => createGroup(name),
    onSuccess: refresh,
  })
  const addCategory = useMutation({
    mutationFn: ({ groupId, name }: { groupId: number; name: string }) =>
      createCategory(groupId, name),
    onSuccess: refresh,
  })
  const renameGroup = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => updateGroup(id, { name }),
    onSuccess: refresh,
  })
  const renameCategory = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      updateCategory(id, { name }),
    onSuccess: refresh,
  })
  const hideGroup = useMutation({
    mutationFn: ({ id, hidden }: { id: number; hidden: boolean }) =>
      updateGroup(id, { hidden }),
    onSuccess: refresh,
  })
  const hideCategory = useMutation({
    mutationFn: ({ id, hidden }: { id: number; hidden: boolean }) =>
      updateCategory(id, { hidden }),
    onSuccess: refresh,
  })
  const moveGroup = useMutation({
    mutationFn: (ids: number[]) => reorderGroups(ids),
    onSuccess: refresh,
  })
  const moveCategory = useMutation({
    mutationFn: ({ groupId, ids }: { groupId: number; ids: number[] }) =>
      reorderCategories(groupId, ids),
    onSuccess: refresh,
  })

  const mutations = [
    addGroup,
    addCategory,
    renameGroup,
    renameCategory,
    hideGroup,
    hideCategory,
    moveGroup,
    moveCategory,
  ]
  // One action runs at a time, so the first failure is the one worth showing.
  // Everything is disabled while one is in flight, so two reorders can't race.
  const busy = mutations.some((mutation) => mutation.isPending)
  const failed = mutations.find((mutation) => mutation.isError)

  const actions: Actions = {
    renameGroup: (id, name) => renameGroup.mutate({ id, name }),
    hideGroup: (id, hidden) => hideGroup.mutate({ id, hidden }),
    moveGroup: (ids) => moveGroup.mutate(ids),
    addCategory: (groupId, name) => addCategory.mutate({ groupId, name }),
    renameCategory: (id, name) => renameCategory.mutate({ id, name }),
    hideCategory: (id, hidden) => hideCategory.mutate({ id, hidden }),
    moveCategory: (groupId, ids) => moveCategory.mutate({ groupId, ids }),
  }

  if (groups.isPending) {
    return <p className="text-gray-500">Loading…</p>
  }
  if (groups.isError) {
    return <p className="text-red-700">Could not load categories: {groups.error.message}</p>
  }

  // Moves work on the whole list, hidden rows included, so a reorder here never
  // reshuffles anything that happens to be out of sight.
  const ids = groups.data.map((group) => group.id)
  const shown = showHidden ? groups.data : groups.data.filter((group) => !group.hidden)

  return (
    <div className="space-y-4">
      <NameForm
        placeholder="New group"
        submitLabel="Add group"
        busy={busy}
        onAdd={(name) => addGroup.mutate(name)}
      />
      {failed && <p className="text-sm text-red-700">{failed.error.message}</p>}
      {shown.length === 0 ? (
        <p className="text-gray-500">
          {groups.data.length === 0
            ? 'No groups yet. Add one like “Housing”.'
            : 'Every group is hidden. Tick “Show hidden” to see them.'}
        </p>
      ) : (
        shown.map((group) => {
          const index = ids.indexOf(group.id)
          return (
            <GroupCard
              key={group.id}
              group={group}
              actions={actions}
              busy={busy}
              showHidden={showHidden}
              atTop={index === 0}
              atBottom={index === ids.length - 1}
              onMove={(direction) => moveGroup.mutate(move(ids, index, direction))}
            />
          )
        })
      )}
    </div>
  )
}

function GroupCard({
  group,
  actions,
  busy,
  showHidden,
  atTop,
  atBottom,
  onMove,
}: {
  group: CategoryGroup
  actions: Actions
  busy: boolean
  showHidden: boolean
  atTop: boolean
  atBottom: boolean
  onMove: (direction: Direction) => void
}) {
  // The server sends the categories in order; here they are split into the ones
  // to draw and the positions a move would swap with.
  const ids = group.categories.map((category) => category.id)
  const position = (id: number) => ids.indexOf(id)
  const shown = showHidden
    ? group.categories
    : group.categories.filter((category) => !category.hidden)

  return (
    <section
      aria-label={group.name}
      className="rounded border border-gray-200 bg-white"
    >
      <div className="flex items-center gap-3 border-b border-gray-200 px-3 py-2">
        <EditableName
          value={group.name}
          label={`group “${group.name}”`}
          onSave={(name) => actions.renameGroup(group.id, name)}
        />
        {group.is_income && <Badge>Income</Badge>}
        {group.hidden && <Badge>Hidden</Badge>}
        <span className="ml-auto flex items-center gap-1">
          <MoveButtons
            label={`group “${group.name}”`}
            busy={busy}
            atTop={atTop}
            atBottom={atBottom}
            onMove={onMove}
          />
          <button
            type="button"
            disabled={busy}
            onClick={() => actions.hideGroup(group.id, !group.hidden)}
            className={smallButton}
          >
            {group.hidden ? 'Unhide' : 'Hide'}
          </button>
        </span>
      </div>
      <ul>
        {shown.map((category) => (
          <CategoryRow
            key={category.id}
            category={category}
            actions={actions}
            busy={busy}
            atTop={position(category.id) === 0}
            atBottom={position(category.id) === ids.length - 1}
            onMove={(direction) =>
              actions.moveCategory(group.id, move(ids, position(category.id), direction))
            }
          />
        ))}
      </ul>
      <div className="px-3 py-2">
        <NameForm
          placeholder={`New category in ${group.name}`}
          submitLabel="Add category"
          busy={busy}
          onAdd={(name) => actions.addCategory(group.id, name)}
        />
      </div>
    </section>
  )
}

function CategoryRow({
  category,
  actions,
  busy,
  atTop,
  atBottom,
  onMove,
}: {
  category: Category
  actions: Actions
  busy: boolean
  atTop: boolean
  atBottom: boolean
  onMove: (direction: Direction) => void
}) {
  return (
    <li className="flex items-center gap-2 border-b border-gray-100 px-3 py-1.5 text-sm last:border-0">
      <span className={category.hidden ? 'text-gray-400' : ''}>
        <EditableName
          value={category.name}
          label={`category “${category.name}”`}
          onSave={(name) => actions.renameCategory(category.id, name)}
        />
      </span>
      {category.hidden && <Badge>Hidden</Badge>}
      <span className="ml-auto flex items-center gap-1">
        <MoveButtons
          label={`category “${category.name}”`}
          busy={busy}
          atTop={atTop}
          atBottom={atBottom}
          onMove={onMove}
        />
        <button
          type="button"
          disabled={busy}
          onClick={() => actions.hideCategory(category.id, !category.hidden)}
          className={smallButton}
        >
          {category.hidden ? 'Unhide' : 'Hide'}
        </button>
      </span>
    </li>
  )
}

const smallButton =
  'rounded border border-gray-300 px-2 py-0.5 text-xs hover:bg-gray-100 disabled:opacity-30'

function MoveButtons({
  label,
  busy,
  atTop,
  atBottom,
  onMove,
}: {
  label: string
  busy: boolean
  atTop: boolean
  atBottom: boolean
  onMove: (direction: Direction) => void
}) {
  return (
    <>
      <button
        type="button"
        aria-label={`Move ${label} up`}
        title={`Move ${label} up`}
        disabled={busy || atTop}
        onClick={() => onMove('up')}
        className={smallButton}
      >
        ↑
      </button>
      <button
        type="button"
        aria-label={`Move ${label} down`}
        title={`Move ${label} down`}
        disabled={busy || atBottom}
        onClick={() => onMove('down')}
        className={smallButton}
      >
        ↓
      </button>
    </>
  )
}

// A one-line form: type a name, submit, and the box clears. Adds a group at the
// top of the page and a category inside each group.
function NameForm({
  placeholder,
  submitLabel,
  busy,
  onAdd,
}: {
  placeholder: string
  submitLabel: string
  busy: boolean
  onAdd: (name: string) => void
}) {
  const [name, setName] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    const trimmed = name.trim()
    if (trimmed === '') {
      return
    }
    onAdd(trimmed)
    setName('')
  }

  return (
    <form onSubmit={submit} className="flex items-center gap-2">
      <input
        value={name}
        onChange={(event) => setName(event.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="w-64 rounded border border-gray-300 px-2 py-1 text-sm"
      />
      <button
        type="submit"
        disabled={busy || name.trim() === ''}
        className="rounded border border-gray-300 px-3 py-1 text-sm hover:bg-gray-100 disabled:opacity-50"
      >
        {submitLabel}
      </button>
    </form>
  )
}

function Badge({ children }: { children: string }) {
  return (
    <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
      {children}
    </span>
  )
}
