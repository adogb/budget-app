import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { fetchCountries, fetchInstitutions, type Institution, startLink } from '../api/bank'

export default function LinkBankPage() {
  const [country, setCountry] = useState('DK')
  const countries = useQuery({ queryKey: ['bank-countries'], queryFn: fetchCountries })

  return (
    <section>
      <h1 className="mb-1 text-xl font-semibold">Link a bank</h1>
      <p className="mb-4 text-sm text-gray-600">
        You'll log in at your bank, then come back here to choose which accounts to add.
      </p>
      <label className="mb-4 block text-sm">
        <span className="mr-2 text-gray-600">Country</span>
        <select
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          className="rounded border border-gray-300 bg-white px-2 py-1"
        >
          {(countries.data ?? [{ code: 'DK', name: 'Denmark', flag: '🇩🇰' }]).map((c) => (
            <option key={c.code} value={c.code}>
              {c.flag} {c.name}
            </option>
          ))}
        </select>
      </label>
      {/* A new key per country starts the bank list fresh, search box included. */}
      <BankPicker key={country} country={country} />
    </section>
  )
}

function BankPicker({ country }: { country: string }) {
  const [search, setSearch] = useState('')
  const institutions = useQuery({
    queryKey: ['bank-institutions', country],
    queryFn: () => fetchInstitutions(country),
  })
  const link = useMutation({
    mutationFn: (bank: Institution) => startLink(bank.id, country),
    // Leave the app for the bank's login page; it sends us back to /link/callback.
    onSuccess: (url) => window.location.assign(url),
  })

  if (institutions.isPending) {
    return <p className="text-gray-500">Loading banks…</p>
  }
  if (institutions.isError) {
    return <p className="text-red-700">Could not load banks: {institutions.error.message}</p>
  }

  // Derived from state on every render, so it never gets out of sync with `search`.
  const matches = institutions.data.filter((bank) =>
    bank.name.toLowerCase().includes(search.trim().toLowerCase()),
  )

  return (
    <div>
      <input
        type="search"
        placeholder="Search banks"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="mb-3 w-full rounded border border-gray-300 px-3 py-2 text-sm"
      />
      {link.isError && (
        <p className="mb-3 text-sm text-red-700">Could not start the link: {link.error.message}</p>
      )}
      {matches.length === 0 ? (
        <p className="text-gray-500">No banks match “{search}”.</p>
      ) : (
        <ul className="rounded border border-gray-200 bg-white">
          {matches.map((bank) => (
            <li key={bank.id} className="border-b border-gray-100 last:border-0">
              <button
                type="button"
                disabled={link.isPending}
                onClick={() => link.mutate(bank)}
                className="flex w-full items-center gap-3 px-3 py-2 text-left text-sm hover:bg-gray-50 disabled:opacity-50"
              >
                {bank.logo && <img src={bank.logo} alt="" className="h-6 w-6 object-contain" />}
                {bank.name}
                {link.isPending && link.variables?.id === bank.id && (
                  <span className="ml-auto text-gray-500">Opening your bank…</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
