import { getJson, postJson } from './client'
import type { components } from './schema'

export type Country = components['schemas']['Country']
export type Institution = components['schemas']['Institution']
export type BankLink = components['schemas']['BankLinkOut']
export type LinkAccount = components['schemas']['LinkAccount']
export type SyncResult = components['schemas']['SyncResultOut']

export function fetchCountries(): Promise<Country[]> {
  return getJson<Country[]>('/api/bank/countries')
}

export function fetchInstitutions(country: string): Promise<Institution[]> {
  return getJson<Institution[]>(`/api/bank/institutions?country=${encodeURIComponent(country)}`)
}

export function fetchBankLinks(): Promise<BankLink[]> {
  return getJson<BankLink[]>('/api/bank/links')
}

// Returns the bank's login page. The bank sends the user back to /link/callback.
export async function startLink(institutionId: string, countryCode: string): Promise<string> {
  const { link } = await postJson<{ link: string }>('/api/bank/links', {
    institution_id: institutionId,
    country_code: countryCode,
    redirect_url: `${window.location.origin}/link/callback`,
  })
  return link
}

export function fetchLinkAccounts(reference: string): Promise<LinkAccount[]> {
  return getJson<LinkAccount[]>(`/api/bank/links/${encodeURIComponent(reference)}/accounts`)
}

export function completeLink(reference: string, externalIds: string[]): Promise<void> {
  return postJson<void>(`/api/bank/links/${encodeURIComponent(reference)}/complete`, {
    external_ids: externalIds,
  })
}

export function syncAll(): Promise<SyncResult[]> {
  return postJson<SyncResult[]>('/api/bank/sync')
}
