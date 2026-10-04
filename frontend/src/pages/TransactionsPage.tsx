import { useQuery } from '@tanstack/react-query'
import { fetchTransactions, type Transaction } from '../api/transactions'
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
  const { data, isPending, isError, error } = useQuery({
    queryKey: ['transactions'],
    queryFn: fetchTransactions,
  })

  if (isPending) {
    return <p className="text-gray-500">Loading…</p>
  }
  if (isError) {
    return <p className="text-red-700">Could not load transactions: {error.message}</p>
  }
  if (data.length === 0) {
    return <p className="text-gray-500">No transactions yet</p>
  }
  return <TransactionsTable transactions={data} />
}

function TransactionsTable({ transactions }: { transactions: Transaction[] }) {
  return (
    <table className="w-full rounded border border-gray-200 bg-white text-sm">
      <thead className="border-b border-gray-200 text-left text-gray-600">
        <tr>
          <th className="px-3 py-2 font-medium">Date</th>
          <th className="px-3 py-2 font-medium">Description</th>
          <th className="px-3 py-2 text-right font-medium">Amount</th>
        </tr>
      </thead>
      <tbody>
        {transactions.map((t) => (
          <tr key={t.id} className="border-b border-gray-100 last:border-0">
            <td className="px-3 py-2 whitespace-nowrap text-gray-600">{t.booking_date}</td>
            <td className="px-3 py-2">{t.description}</td>
            <td className="px-3 py-2 text-right whitespace-nowrap">
              <Money value={t.amount} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
