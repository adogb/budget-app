import { describe, expect, test } from 'vitest'
import { formatMoney } from './money'

// Intl puts a non-breaking space (U+00A0) between the number and "kr.".
const NBSP = String.fromCharCode(0xa0)

describe('formatMoney', () => {
  test('negative amount with thousands separator', () => {
    expect(formatMoney({ amount: -250000, currency: 'DKK' })).toBe(`-2.500,00${NBSP}kr.`)
  })

  test('zero', () => {
    expect(formatMoney({ amount: 0, currency: 'DKK' })).toBe(`0,00${NBSP}kr.`)
  })

  test('positive amount with øre', () => {
    expect(formatMoney({ amount: 1250, currency: 'DKK' })).toBe(`12,50${NBSP}kr.`)
  })
})
