export type Direction = 'up' | 'down'

// move() returns a new array with the item at `index` swapped with the one
// next to it in `direction`, or the same items when it is already at that end.
// The up/down buttons on the Categories page use it, then send the whole order
// to the API (plan 03 C2).
export function move<T>(items: T[], index: number, direction: Direction): T[] {
  const target = direction === 'up' ? index - 1 : index + 1
  if (target < 0 || target >= items.length) {
    return items
  }
  const moved = [...items]
  moved[index] = items[target]
  moved[target] = items[index]
  return moved
}
