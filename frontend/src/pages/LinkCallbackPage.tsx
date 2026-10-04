import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { completeLink, fetchLinkAccounts, type LinkAccount } from '../api/bank'

// The bank sends the user back here as /link/callback?ref=<reference>.
export default function LinkCallbackPage() {
  const [searchParams] = useSearchParams()
  const reference = searchParams.get('ref')

  return (
    <section>
      <h1 className="mb-4 text-xl font-semibold">Choose accounts</h1>
      {reference ? (
        <CallbackContent reference={reference} />
      ) : (
        <TryAgain message="This page needs a bank link reference." />
      )}
    </section>
  )
}

function CallbackContent({ reference }: { reference: string }) {
  const accounts = useQuery({
    queryKey: ['link-accounts', reference],
    queryFn: () => fetchLinkAccounts(reference),
  })

  if (accounts.isPending) {
    return <p className="text-gray-500">Loading your accounts…</p>
  }
  if (accounts.isError) {
    return <TryAgain message={`Could not load your accounts: ${accounts.error.message}`} />
  }
  if (accounts.data.length === 0) {
    return <TryAgain message="The bank didn't share any accounts. Did you cancel at the bank?" />
  }
  // Only rendered once the accounts are loaded, so its initial state can use them.
  return <AccountChooser reference={reference} accounts={accounts.data} />
}

function AccountChooser({ reference, accounts }: { reference: string; accounts: LinkAccount[] }) {
  // When renewing, the accounts you already have start ticked.
  const [chosen, setChosen] = useState<string[]>(() =>
    accounts.filter((a) => a.eligible && a.already_linked).map((a) => a.external_id),
  )
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const save = useMutation({
    mutationFn: () => completeLink(reference, chosen),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['accounts'] })
      await queryClient.invalidateQueries({ queryKey: ['bank-links'] })
      navigate('/accounts')
    },
  })

  function toggle(externalId: string, checked: boolean) {
    // A new array, never a changed one, so React sees the update.
    setChosen(checked ? [...chosen, externalId] : chosen.filter((id) => id !== externalId))
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        save.mutate()
      }}
    >
      <ul className="mb-4 rounded border border-gray-200 bg-white">
        {accounts.map((account) => (
          <li key={account.external_id} className="border-b border-gray-100 last:border-0">
            <label
              className={`flex items-center gap-3 px-3 py-2 text-sm ${account.eligible ? '' : 'text-gray-400'}`}
            >
              <input
                type="checkbox"
                disabled={!account.eligible}
                checked={chosen.includes(account.external_id)}
                onChange={(e) => toggle(account.external_id, e.target.checked)}
              />
              <span>
                <span className="block">{account.name}</span>
                <span className="block text-gray-500">
                  {account.iban ?? 'No IBAN'} · {account.currency}
                  {!account.eligible && ' · only DKK accounts can be budgeted'}
                  {account.already_linked && ' · already added'}
                </span>
              </span>
            </label>
          </li>
        ))}
      </ul>
      {save.isError && <p className="mb-3 text-sm text-red-700">{save.error.message}</p>}
      <button
        type="submit"
        disabled={chosen.length === 0 || save.isPending}
        className="rounded bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
      >
        {save.isPending ? 'Saving…' : `Add ${chosen.length} account${chosen.length === 1 ? '' : 's'}`}
      </button>
    </form>
  )
}

function TryAgain({ message }: { message: string }) {
  return (
    <p className="text-gray-700">
      {message}{' '}
      <Link to="/link" className="text-blue-700 hover:underline">
        Link a bank again
      </Link>
    </p>
  )
}
