import { describe, expect, it } from 'vitest'
import { move } from './reorder'

describe('move', () => {
  it('swaps an item with its neighbour', () => {
    expect(move(['a', 'b', 'c'], 2, 'up')).toEqual(['a', 'c', 'b'])
    expect(move(['a', 'b', 'c'], 0, 'down')).toEqual(['b', 'a', 'c'])
  })

  it('does nothing at the ends', () => {
    const ids = ['a', 'b', 'c']

    expect(move(ids, 0, 'up')).toEqual(ids)
    expect(move(ids, 2, 'down')).toEqual(ids)
  })

  it('leaves the array it was given alone', () => {
    const ids = ['a', 'b', 'c']

    move(ids, 2, 'up')

    expect(ids).toEqual(['a', 'b', 'c'])
  })
})
