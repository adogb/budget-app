import { useQuery } from '@tanstack/react-query'
import {
  type Category,
  type CategoryGroup,
  fetchCategoryGroups,
} from '../api/categories'

export default function CategoriesPage() {
  return (
    <section>
      <h1 className="mb-4 text-xl font-semibold">Categories</h1>
      <CategoriesContent />
    </section>
  )
}

function CategoriesContent() {
  const groups = useQuery({ queryKey: ['category-groups'], queryFn: fetchCategoryGroups })

  if (groups.isPending) {
    return <p className="text-gray-500">Loading…</p>
  }
  if (groups.isError) {
    return <p className="text-red-700">Could not load categories: {groups.error.message}</p>
  }
  if (groups.data.length === 0) {
    return <p className="text-gray-500">No groups yet. Add one like “Housing”.</p>
  }

  // The API sends both levels in order, so the page renders what it is given.
  return (
    <div className="space-y-4">
      {groups.data.map((group) => (
        <GroupCard key={group.id} group={group} />
      ))}
    </div>
  )
}

function GroupCard({ group }: { group: CategoryGroup }) {
  return (
    <div className="rounded border border-gray-200 bg-white">
      <div className="flex items-center gap-3 border-b border-gray-200 px-3 py-2">
        <h2 className="font-medium">{group.name}</h2>
        {group.is_income && <Badge>Income</Badge>}
        {group.hidden && <Badge>Hidden</Badge>}
      </div>
      <ul>
        {group.categories.map((category) => (
          <CategoryRow key={category.id} category={category} />
        ))}
      </ul>
    </div>
  )
}

function CategoryRow({ category }: { category: Category }) {
  return (
    <li className="flex items-center gap-2 border-b border-gray-100 px-3 py-1.5 text-sm last:border-0">
      <span className={category.hidden ? 'text-gray-400' : ''}>{category.name}</span>
      {category.hidden && <Badge>Hidden</Badge>}
    </li>
  )
}

function Badge({ children }: { children: string }) {
  return (
    <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
      {children}
    </span>
  )
}
