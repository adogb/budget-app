import type { components } from '../api/schema'

export type Money = components['schemas']['Money']

// Amounts arrive in minor units (øre for DKK). The currency's number of
// decimals tells us how far to shift, so 2 for DKK and 0 for JPY.
export function formatMoney({ amount, currency }: Money): string {
  const formatter = new Intl.NumberFormat('da-DK', { style: 'currency', currency })
  const decimals = formatter.resolvedOptions().maximumFractionDigits ?? 0
  return formatter.format(amount / 10 ** decimals)
}
