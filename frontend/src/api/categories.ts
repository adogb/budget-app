import { getJson, patchJson, postJson, putJson } from './client'
import type { components } from './schema'

export type CategoryGroup = components['schemas']['CategoryGroupOut']
export type Category = components['schemas']['CategoryOut']
export type GroupChanges = components['schemas']['GroupPatch']
export type CategoryChanges = components['schemas']['CategoryPatch']

export function fetchCategoryGroups(): Promise<CategoryGroup[]> {
  return getJson<CategoryGroup[]>('/api/category-groups')
}

export function createGroup(name: string, isIncome = false): Promise<CategoryGroup> {
  return postJson<CategoryGroup>('/api/category-groups', { name, is_income: isIncome })
}

export function updateGroup(id: number, changes: GroupChanges): Promise<CategoryGroup> {
  return patchJson<CategoryGroup>(`/api/category-groups/${id}`, changes)
}

// The whole order, not a swap: see plan 03 C2.
export function reorderGroups(ids: number[]): Promise<void> {
  return putJson<void>('/api/category-groups/order', { ids })
}

export function createCategory(groupId: number, name: string): Promise<Category> {
  return postJson<Category>('/api/categories', { group_id: groupId, name })
}

export function updateCategory(id: number, changes: CategoryChanges): Promise<Category> {
  return patchJson<Category>(`/api/categories/${id}`, changes)
}

export function reorderCategories(groupId: number, ids: number[]): Promise<void> {
  return putJson<void>(`/api/category-groups/${groupId}/categories/order`, { ids })
}
