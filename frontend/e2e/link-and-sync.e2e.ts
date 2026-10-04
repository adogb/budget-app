import { expect, type Page, test } from '@playwright/test'

// The golden path of slice 2: link a bank, choose accounts, sync, see
// transactions. The API is faked in the browser, so neither the backend nor
// GoCardless is involved.

const dkk = (amount: number) => ({ amount, currency: 'DKK' })
const inNinetyDays = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString()

async function fakeApi(page: Page) {
  // What the fake server knows; requests below change it as the real one would.
  const state = {
    accounts: [] as object[],
    links: [] as object[],
    transactions: [] as object[],
    pending: [] as object[],
  }
  const json = (body: unknown) => ({ json: body })

  await page.route('**/api/accounts', (route) => route.fulfill(json(state.accounts)))
  await page.route('**/api/transactions', (route) => route.fulfill(json(state.transactions)))
  await page.route('**/api/transactions/pending', (route) =>
    route.fulfill(json(state.pending)),
  )
  await page.route('**/api/bank/countries', (route) =>
    route.fulfill(json([{ code: 'DK', name: 'Denmark', flag: '🇩🇰' }])),
  )
  await page.route('**/api/bank/institutions?country=DK', (route) =>
    route.fulfill(json([{ id: 'BANK_DK', name: 'Danske Test', logo: '', countries: ['DK'] }])),
  )
  await page.route('**/api/bank/links', (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill(json(state.links))
    }
    // The real bank would show its login page first, then send us back here.
    return route.fulfill(json({ link: 'http://localhost:5173/link/callback?ref=ref-1' }))
  })
  await page.route('**/api/bank/links/ref-1/accounts', (route) =>
    route.fulfill(
      json([
        {
          external_id: 'acc-1',
          name: 'Checking',
          iban: 'DK0001',
          currency: 'DKK',
          eligible: true,
          already_linked: false,
        },
        {
          external_id: 'acc-eur',
          name: 'Euro savings',
          iban: 'DE0002',
          currency: 'EUR',
          eligible: false,
          already_linked: false,
        },
      ]),
    ),
  )
  await page.route('**/api/bank/links/ref-1/complete', (route) => {
    expect(route.request().postDataJSON()).toEqual({ external_ids: ['acc-1'] })
    state.links = [
      {
        id: 1,
        institution_id: 'BANK_DK',
        country_code: 'DK',
        bank_name: 'Danske Test',
        expires_at: inNinetyDays,
        consent_status: 'ok',
        account_ids: [1],
      },
    ]
    state.accounts = [
      {
        id: 1,
        name: 'Checking',
        bank_name: 'Danske Test',
        iban: 'DK0001',
        balance: dkk(1234500),
        bank_integration_id: 1,
        last_synced_at: null,
      },
    ]
    return route.fulfill({ status: 204 })
  })
  await page.route('**/api/bank/sync', (route) => {
    state.transactions = [
      {
        id: 't-1',
        account_id: 1,
        booking_date: '2026-10-02',
        value_date: null,
        description: 'Netto',
        payee: 'Netto Nørrebro',
        notes: null,
        amount: dkk(-25000),
      },
    ]
    state.pending = [
      {
        id: 1,
        account_id: 1,
        booking_date: null,
        description: 'Taxi',
        payee: null,
        amount: dkk(-14900),
      },
    ]
    return route.fulfill(
      json([{ account_id: 1, account_name: 'Checking', new_transactions: 1, error: null }]),
    )
  })
}

test('link a bank, choose accounts, sync and see transactions', async ({ page }) => {
  await fakeApi(page)

  await page.goto('/accounts')
  await expect(page.getByText('No accounts yet')).toBeVisible()
  await page.getByRole('link', { name: 'Link a bank' }).click()

  await page.getByPlaceholder('Search banks').fill('danske')
  await page.getByRole('button', { name: 'Danske Test' }).click()

  // Back from the "bank": only the DKK account can be chosen.
  await expect(page.getByRole('heading', { name: 'Choose accounts' })).toBeVisible()
  await expect(page.getByRole('checkbox', { name: /Euro savings/ })).toBeDisabled()
  await page.getByRole('checkbox', { name: /Checking/ }).check()
  await page.getByRole('button', { name: 'Add 1 account' }).click()

  await expect(page).toHaveURL(/\/accounts$/)
  await expect(page.getByRole('heading', { name: 'Danske Test' })).toBeVisible()
  await expect(page.getByText('Never synced')).toBeVisible()

  await page.getByRole('button', { name: 'Sync with bank' }).click()
  await expect(page.getByText('Imported 1 new transaction.')).toBeVisible()

  await page.getByRole('link', { name: 'Transactions' }).click()
  await expect(page.getByRole('row', { name: /Netto/ })).toBeVisible()
  const taxi = page.getByRole('row', { name: /Taxi/ })
  await expect(taxi).toContainText('Pending')
})
