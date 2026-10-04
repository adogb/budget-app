import type { BankLink } from '../api/bank'
import { daysUntil, formatDate } from '../lib/dates'

// Bank consent lasts 90 days; the API flags it "expiring" 7 days before.
export default function ConsentBadge({ link }: { link: BankLink }) {
  if (link.consent_status === 'expired' || link.expires_at === null) {
    return <span className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-800">Expired</span>
  }
  if (link.consent_status === 'expiring') {
    const days = daysUntil(link.expires_at)
    return (
      <span className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
        Expires in {days} day{days === 1 ? '' : 's'}
      </span>
    )
  }
  return (
    <span className="text-xs text-gray-500">Consent until {formatDate(link.expires_at)}</span>
  )
}
