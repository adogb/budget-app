import { getJson } from './client'
import type { components } from './schema'

export type Transaction = components['schemas']['TransactionOut']

export function fetchTransactions(): Promise<Transaction[]> {
  return getJson<Transaction[]>('/api/transactions')
}
