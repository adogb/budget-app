import { expect, type Page, test } from '@playwright/test'

// The golden path of slice 3: build a tree, rename, hide and reorder. The API
// is faked in the browser, so neither the backend nor the database is involved.

type Category = {
  id: number
  group_id: number
  name: string
  hidden: boolean
  sort_order: number
}

type Group = {
  id: number
  name: string
  is_income: boolean
  hidden: boolean
  sort_order: number
  categories: Category[]
}

// A fake server that remembers what it has been told, so the page can be
// driven through a whole session. The requests that change order are kept, so
// a test can check what the arrows actually sent.
async function fakeApi(page: Page) {
  const state: { groups: Group[]; nextId: number } = { groups: [], nextId: 1 }
  const sentGroups: number[][] = []
  const sentCategories: number[][] = []

  const json = (body: unknown, status = 200) => ({ status, json: body })
  const idFromUrl = (url: string) => Number(new URL(url).pathname.split('/').pop())
  const allCategories = () => state.groups.flatMap((group) => group.categories)
  const reorder = <T extends { id: number; sort_order: number }>(
    items: T[],
    ids: number[],
  ) => {
    items.sort((a, b) => ids.indexOf(a.id) - ids.indexOf(b.id))
    items.forEach((item, index) => {
      item.sort_order = index
    })
  }

  await page.route('**/api/category-groups', (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill(json(state.groups))
    }
    const body = route.request().postDataJSON()
    const group: Group = {
      id: state.nextId++,
      name: body.name,
      is_income: body.is_income ?? false,
      hidden: false,
      sort_order: state.groups.length,
      categories: [],
    }
    state.groups.push(group)
    return route.fulfill(json(group, 201))
  })

  await page.route('**/api/category-groups/*/categories/order', (route) => {
    const { ids } = route.request().postDataJSON()
    const groupId = Number(new URL(route.request().url()).pathname.split('/').at(-3))
    const group = state.groups.find((candidate) => candidate.id === groupId)
    sentCategories.push(ids)
    if (group) {
      reorder(group.categories, ids)
    }
    return route.fulfill({ status: 204 })
  })

  await page.route('**/api/category-groups/*', (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/order')) {
      const { ids } = route.request().postDataJSON()
      sentGroups.push(ids)
      reorder(state.groups, ids)
      return route.fulfill({ status: 204 })
    }
    const group = state.groups.find((candidate) => candidate.id === idFromUrl(path))
    if (group) {
      Object.assign(group, route.request().postDataJSON())
    }
    return route.fulfill(json(group))
  })

  await page.route('**/api/categories', (route) => {
    const body = route.request().postDataJSON()
    const group = state.groups.find((candidate) => candidate.id === body.group_id)
    const category: Category = {
      id: state.nextId++,
      group_id: body.group_id,
      name: body.name,
      hidden: false,
      sort_order: group ? group.categories.length : 0,
    }
    group?.categories.push(category)
    return route.fulfill(json(category, 201))
  })

  await page.route('**/api/categories/*', (route) => {
    const category = allCategories().find(
      (candidate) => candidate.id === idFromUrl(route.request().url()),
    )
    if (category) {
      Object.assign(category, route.request().postDataJSON())
    }
    return route.fulfill(json(category))
  })

  return {
    sentGroups,
    sentCategories,
    groupId: (name: string) => state.groups.find((group) => group.name === name)?.id,
    categoryId: (name: string) =>
      allCategories().find((category) => category.name === name)?.id,
  }
}

test('build a tree, then rename, hide and reorder', async ({ page }) => {
  const api = await fakeApi(page)

  await page.goto('/categories')
  await expect(page.getByText('No groups yet')).toBeVisible()

  // Two groups.
  await page.getByLabel('New group').fill('Housing')
  await page.getByRole('button', { name: 'Add group' }).click()
  await page.getByLabel('New group').fill('Travel')
  await page.getByRole('button', { name: 'Add group' }).click()

  const housing = page.getByRole('region', { name: 'Housing' })
  await expect(housing).toBeVisible()

  // The first group can't move up and the last can't move down.
  await expect(page.getByRole('button', { name: 'Move group “Housing” up' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Move group “Travel” down' })).toBeDisabled()

  await page.getByRole('button', { name: 'Move group “Travel” up' }).click()

  const groupNames = page.getByRole('button', { name: /^(Housing|Travel)$/ })
  await expect(groupNames).toHaveText(['Travel', 'Housing'])
  expect(api.sentGroups.at(-1)).toEqual([api.groupId('Travel'), api.groupId('Housing')])

  // Two categories in Housing.
  const newCategory = housing.getByLabel('New category in Housing')
  await newCategory.fill('Rent')
  await housing.getByRole('button', { name: 'Add category' }).click()
  await newCategory.fill('Electricity')
  await housing.getByRole('button', { name: 'Add category' }).click()

  const rows = housing.getByRole('listitem')
  await expect(rows).toHaveText([/Rent/, /Electricity/])

  // Rename by clicking the name: Enter saves, Escape doesn't.
  await housing.getByRole('button', { name: 'Rent', exact: true }).click()
  await housing.getByLabel('Rename category “Rent”').fill('Rent and fees')
  await housing.getByLabel('Rename category “Rent”').press('Enter')
  await expect(housing.getByRole('button', { name: 'Rent and fees', exact: true })).toBeVisible()

  await housing.getByRole('button', { name: 'Rent and fees', exact: true }).click()
  await housing.getByLabel('Rename category “Rent and fees”').fill('Nope')
  await housing.getByLabel('Rename category “Rent and fees”').press('Escape')
  await expect(housing.getByRole('button', { name: 'Rent and fees', exact: true })).toBeVisible()

  // Hiding takes it out of the way, unless hidden rows are asked for.
  const fees = rows.filter({ hasText: 'Rent and fees' })
  await fees.getByRole('button', { name: 'Hide' }).click()
  await expect(rows).toHaveText([/Electricity/])

  await page.getByLabel('Show hidden').check()
  await expect(rows).toHaveText([/Rent and fees/, /Electricity/])
  await expect(rows.filter({ hasText: 'Rent and fees' })).toContainText('Hidden')

  // Moving a row up sends the whole new order, hidden rows included.
  await housing.getByRole('button', { name: 'Move category “Electricity” up' }).click()
  await expect(rows).toHaveText([/Electricity/, /Rent and fees/])
  expect(api.sentCategories.at(-1)).toEqual([
    api.categoryId('Electricity'),
    api.categoryId('Rent and fees'),
  ])
})
