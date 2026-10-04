import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { fetchBankLinks } from '../api/bank'
import ConsentBadge from './ConsentBadge'

// Shown on other pages so an expiring consent is noticed before syncing stops.
export default function ConsentBanner() {
  const links = useQuery({ queryKey: ['bank-links'], queryFn: fetchBankLinks })
  const needsRenewal = (links.data ?? []).filter((link) => link.consent_status !== 'ok')

  if (needsRenewal.length === 0) {
    return null
  }
  return (
    <div className="mb-4 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm">
      {needsRenewal.map((link) => (
        <p key={link.id} className="flex items-center gap-2">
          Bank consent for {link.bank_name}: <ConsentBadge link={link} />
          <Link to="/accounts" className="text-blue-700 hover:underline">
            Renew on the Accounts page
          </Link>
        </p>
      ))}
    </div>
  )
}
