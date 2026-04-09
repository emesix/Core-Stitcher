import { statusColor, statusSymbol } from '../../types'

interface Props { status: string }

export function StatusBadge({ status }: Props) {
  return (
    <span style={{ color: statusColor(status), fontWeight: 'bold' }}>
      {statusSymbol(status)} {status.toUpperCase()}
    </span>
  )
}
