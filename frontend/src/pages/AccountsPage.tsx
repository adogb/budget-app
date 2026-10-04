import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { type Account, fetchAccounts } from '../api/accounts'
import { type BankLink, fetchBankLinks } from '../api/bank'
import Money from '../components/Money'
import { formatDateTime } from '../lib/dates'

export default function AccountsPage() {
  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Accounts</h1>
        <Link
          to="/link"
          className="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm hover:bg-gray-100"
        >
          Link a bank
        </Link>
      </div>
      <AccountsContent />
    </section>
  )
}

function AccountsContent() {
  const accounts = useQuery({ queryKey: ['accounts'], queryFn: fetchAccounts })
  const links = useQuery({ queryKey: ['bank-links'], queryFn: fetchBankLinks })

  if (accounts.isPending || links.isPending) {
    return <p className="text-gray-500">Loading…</p>
  }
  if (accounts.isError) {
    return <p className="text-red-700">Could not load accounts: {accounts.error.message}</p>
  }
  if (links.isError) {
    return <p className="text-red-700">Could not load bank links: {links.error.message}</p>
  }
  if (accounts.data.length === 0) {
    return <p className="text-gray-500">No accounts yet. Link a bank to get started.</p>
  }
  return (
    <div className="space-y-6">
      {links.data.map((link) => (
        <BankLinkCard
          key={link.id}
          link={link}
          accounts={accounts.data.filter((a) => a.bank_integration_id === link.id)}
        />
      ))}
    </div>
  )
}

function BankLinkCard({ link, accounts }: { link: BankLink; accounts: Account[] }) {
  return (
    <div className="rounded border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-3 py-2">
        <h2 className="font-medium">{link.bank_name}</h2>
      </div>
      <ul>
        {accounts.map((account) => (
          <AccountRow key={account.id} account={account} />
        ))}
      </ul>
    </div>
  )
}

function AccountRow({ account }: { account: Account }) {
  return (
    <li className="flex items-center justify-between border-b border-gray-100 px-3 py-2 text-sm last:border-0">
      <div>
        <div>{account.name}</div>
        <div className="text-gray-500">
          {account.iban ?? 'No IBAN'} ·{' '}
          {account.last_synced_at
            ? `Synced ${formatDateTime(account.last_synced_at)}`
            : 'Never synced'}
        </div>
      </div>
      <Money value={account.balance} />
    </li>
  )
}
