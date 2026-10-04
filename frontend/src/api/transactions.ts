import { getJson } from './client'
import type { components } from './schema'

export type Transaction = components['schemas']['TransactionOut']
export type PendingTransaction = components['schemas']['PendingTransactionOut']

export function fetchTransactions(): Promise<Transaction[]> {
  return getJson<Transaction[]>('/api/transactions')
}

export function fetchPendingTransactions(): Promise<PendingTransaction[]> {
  return getJson<PendingTransaction[]>('/api/transactions/pending')
}
