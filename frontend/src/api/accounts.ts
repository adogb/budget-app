import { getJson } from './client'
import type { components } from './schema'

export type Account = components['schemas']['AccountOut']

export function fetchAccounts(): Promise<Account[]> {
  return getJson<Account[]>('/api/accounts')
}
