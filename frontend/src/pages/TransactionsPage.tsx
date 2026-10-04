import { useQuery } from '@tanstack/react-query'
import {
  fetchPendingTransactions,
  fetchTransactions,
  type PendingTransaction,
  type Transaction,
} from '../api/transactions'
import ConsentBanner from '../components/ConsentBanner'
import Money from '../components/Money'

export default function TransactionsPage() {
  return (
    <section>
      <h1 className="mb-4 text-xl font-semibold">Transactions</h1>
      <ConsentBanner />
      <TransactionsContent />
    </section>
  )
}

function TransactionsContent() {
  const transactions = useQuery({ queryKey: ['transactions'], queryFn: fetchTransactions })
  const pending = useQuery({
    queryKey: ['pending-transactions'],
    queryFn: fetchPendingTransactions,
  })

  if (transactions.isPending || pending.isPending) {
    return <p className="text-gray-500">Loading…</p>
  }
  if (transactions.isError) {
    return (
      <p className="text-red-700">Could not load transactions: {transactions.error.message}</p>
    )
  }
  if (pending.isError) {
    return (
      <p className="text-red-700">Could not load pending transactions: {pending.error.message}</p>
    )
  }
  if (transactions.data.length === 0 && pending.data.length === 0) {
    return <p className="text-gray-500">No transactions yet</p>
  }
  return <TransactionsTable transactions={transactions.data} pending={pending.data} />
}

function TransactionsTable({
  transactions,
  pending,
}: {
  transactions: Transaction[]
  pending: PendingTransaction[]
}) {
  return (
    <table className="w-full rounded border border-gray-200 bg-white text-sm">
      <thead className="border-b border-gray-200 text-left text-gray-600">
        <tr>
          <th className="px-3 py-2 font-medium">Date</th>
          <th className="px-3 py-2 font-medium">Description</th>
          <th className="px-3 py-2 font-medium">Payee</th>
          <th className="px-3 py-2 text-right font-medium">Amount</th>
        </tr>
      </thead>
      <tbody>
        {/* Pending rows are read-only and don't count in the budget (spec D4). */}
        {pending.map((p) => (
          <tr key={`pending-${p.id}`} className="border-b border-gray-100 opacity-50">
            <td className="px-3 py-2 whitespace-nowrap text-gray-600">{p.booking_date ?? '—'}</td>
            <td className="px-3 py-2">
              {p.description}{' '}
              <span className="ml-1 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
                Pending
              </span>
            </td>
            <td className="px-3 py-2 text-gray-600">{p.payee ?? '—'}</td>
            <td className="px-3 py-2 text-right whitespace-nowrap">
              <Money value={p.amount} />
            </td>
          </tr>
        ))}
        {transactions.map((t) => (
          <tr key={t.id} className="border-b border-gray-100 last:border-0">
            <td className="px-3 py-2 whitespace-nowrap text-gray-600">{t.booking_date}</td>
            <td className="px-3 py-2">{t.description}</td>
            <td className="px-3 py-2 text-gray-600">{t.payee ?? '—'}</td>
            <td className="px-3 py-2 text-right whitespace-nowrap">
              <Money value={t.amount} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
