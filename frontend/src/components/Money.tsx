import { formatMoney, type Money as MoneyValue } from '../lib/money'

type Props = { value: MoneyValue }

export default function Money({ value }: Props) {
  const color = value.amount < 0 ? 'text-gray-900' : 'text-green-700'
  return <span className={`tabular-nums ${color}`}>{formatMoney(value)}</span>
}
