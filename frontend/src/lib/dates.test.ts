import { describe, expect, it } from 'vitest'
import { daysUntil } from './dates'

describe('daysUntil', () => {
  const now = new Date('2026-10-04T12:00:00Z')

  it('rounds partial days up', () => {
    expect(daysUntil('2026-10-06T00:00:00Z', now)).toBe(2)
    expect(daysUntil('2026-10-04T13:00:00Z', now)).toBe(1)
  })

  it('is zero or negative once expired', () => {
    expect(daysUntil('2026-10-04T12:00:00Z', now)).toBe(0)
    expect(daysUntil('2026-10-01T12:00:00Z', now)).toBe(-3)
  })
})
