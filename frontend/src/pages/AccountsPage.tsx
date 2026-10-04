import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router'
import { type Account, fetchAccounts } from '../api/accounts'
import { type BankLink, fetchBankLinks, type SyncResult, startLink, syncAll } from '../api/bank'
import ConsentBadge from '../components/ConsentBadge'
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

// GoCardless allows only a few calls per account per day, so syncing only
// happens when you press the button.
function SyncPanel() {
  const queryClient = useQueryClient()
  const sync = useMutation({
    mutationFn: syncAll,
    onSuccess: () => {
      for (const key of ['accounts', 'bank-links', 'transactions', 'pending-transactions']) {
        queryClient.invalidateQueries({ queryKey: [key] })
      }
    },
  })

  return (
    <div className="mb-6">
      <button
        type="button"
        onClick={() => sync.mutate()}
        disabled={sync.isPending}
        className="rounded bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
      >
        {sync.isPending ? 'Syncing…' : 'Sync with bank'}
      </button>
      {sync.isError && (
        <p className="mt-2 text-sm text-red-700">Sync failed: {sync.error.message}</p>
      )}
      {sync.isSuccess && <SyncSummary results={sync.data} />}
    </div>
  )
}

function SyncSummary({ results }: { results: SyncResult[] }) {
  const imported = results.reduce((sum, r) => sum + (r.new_transactions ?? 0), 0)
  const failed = results.filter((r) => r.error !== null)
  return (
    <div className="mt-2 text-sm">
      <p className="text-gray-700">
        Imported {imported} new transaction{imported === 1 ? '' : 's'}.
      </p>
      {failed.map((r) => (
        <p key={r.account_id} className="text-red-700">
          {r.account_name}: {r.error}
        </p>
      ))}
    </div>
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
      <SyncPanel />
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
      <div className="flex items-center gap-3 border-b border-gray-200 px-3 py-2">
        <h2 className="font-medium">{link.bank_name}</h2>
        <ConsentBadge link={link} />
        {link.consent_status !== 'ok' && <RenewButton link={link} />}
      </div>
      <ul>
        {accounts.map((account) => (
          <AccountRow key={account.id} account={account} />
        ))}
      </ul>
    </div>
  )
}

// Renewing is linking the same bank again. On the way back, the accounts are
// matched to the ones you have, so their transactions stay.
function RenewButton({ link }: { link: BankLink }) {
  const renew = useMutation({
    mutationFn: () => startLink(link.institution_id, link.country_code),
    onSuccess: (url) => window.location.assign(url),
  })
  return (
    <>
      <button
        type="button"
        onClick={() => renew.mutate()}
        disabled={renew.isPending}
        className="ml-auto rounded border border-gray-300 px-3 py-1 text-sm hover:bg-gray-100 disabled:opacity-50"
      >
        {renew.isPending ? 'Opening your bank…' : 'Renew'}
      </button>
      {renew.isError && <span className="text-sm text-red-700">{renew.error.message}</span>}
    </>
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
