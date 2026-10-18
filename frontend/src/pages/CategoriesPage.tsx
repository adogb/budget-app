import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import {
  type Category,
  type CategoryGroup,
  createCategory,
  createGroup,
  fetchCategoryGroups,
  updateCategory,
  updateGroup,
} from '../api/categories'
import EditableName from '../components/EditableName.tsx'

// What a row can ask the page to do. The page owns the mutations, so the rows
// stay presentational.
type Actions = {
  renameGroup: (id: number, name: string) => void
  addCategory: (groupId: number, name: string) => void
  renameCategory: (id: number, name: string) => void
}

export default function CategoriesPage() {
  return (
    <section>
      <h1 className="mb-4 text-xl font-semibold">Categories</h1>
      <CategoriesContent />
    </section>
  )
}

function CategoriesContent() {
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

  const mutations = [addGroup, addCategory, renameGroup, renameCategory]
  const busy = mutations.some((mutation) => mutation.isPending)
  // One action runs at a time, so the first failure is the one worth showing.
  const failed = mutations.find((mutation) => mutation.isError)

  const actions: Actions = {
    renameGroup: (id, name) => renameGroup.mutate({ id, name }),
    addCategory: (groupId, name) => addCategory.mutate({ groupId, name }),
    renameCategory: (id, name) => renameCategory.mutate({ id, name }),
  }

  if (groups.isPending) {
    return <p className="text-gray-500">Loading…</p>
  }
  if (groups.isError) {
    return <p className="text-red-700">Could not load categories: {groups.error.message}</p>
  }

  return (
    <div className="space-y-4">
      <NameForm
        placeholder="New group"
        submitLabel="Add group"
        busy={busy}
        onAdd={(name) => addGroup.mutate(name)}
      />
      {failed && <p className="text-sm text-red-700">{failed.error.message}</p>}
      {groups.data.length === 0 ? (
        <p className="text-gray-500">No groups yet. Add one like “Housing”.</p>
      ) : (
        groups.data.map((group) => (
          <GroupCard key={group.id} group={group} actions={actions} busy={busy} />
        ))
      )}
    </div>
  )
}

function GroupCard({
  group,
  actions,
  busy,
}: {
  group: CategoryGroup
  actions: Actions
  busy: boolean
}) {
  return (
    <div className="rounded border border-gray-200 bg-white">
      <div className="flex items-center gap-3 border-b border-gray-200 px-3 py-2">
        <EditableName
          value={group.name}
          label={`group “${group.name}”`}
          onSave={(name) => actions.renameGroup(group.id, name)}
        />
        {group.is_income && <Badge>Income</Badge>}
        {group.hidden && <Badge>Hidden</Badge>}
      </div>
      <ul>
        {group.categories.map((category) => (
          <CategoryRow key={category.id} category={category} actions={actions} />
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
    </div>
  )
}

function CategoryRow({ category, actions }: { category: Category; actions: Actions }) {
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
    </li>
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
