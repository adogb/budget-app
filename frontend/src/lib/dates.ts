const DAY_MS = 24 * 60 * 60 * 1000

// The API sends timestamps in UTC (ISO 8601); show them in the browser's time zone.
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('da-DK', { dateStyle: 'medium', timeStyle: 'short' })
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('da-DK', { dateStyle: 'medium' })
}

// Whole days left, rounded up: 1.5 days left is "2 days", 1 hour left is "1 day".
export function daysUntil(iso: string, now: Date = new Date()): number {
  return Math.ceil((new Date(iso).getTime() - now.getTime()) / DAY_MS)
}
