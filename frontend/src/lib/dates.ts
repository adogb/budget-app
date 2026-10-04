// The API sends timestamps in UTC (ISO 8601); show them in the browser's time zone.
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('da-DK', { dateStyle: 'medium', timeStyle: 'short' })
}
