import { useState } from 'react'
import './ActivityBar.css'

interface Props {
  onToggleSidebar: () => void
  onToggleBottom: () => void
}

const ITEMS = [
  { icon: '☰', label: 'Explorer', id: 'explorer' },
  { icon: '◎', label: 'Topology', id: 'topology' },
  { icon: '▶', label: 'Runs', id: 'runs' },
  { icon: '✎', label: 'Reviews', id: 'reviews' },
  { icon: '⚙', label: 'System', id: 'system' },
]

export function ActivityBar({ onToggleSidebar, onToggleBottom }: Props) {
  const [active, setActive] = useState('explorer')
  return (
    <div className="activity-bar">
      {ITEMS.map(item => (
        <button
          key={item.id}
          className={`activity-item ${active === item.id ? 'active' : ''}`}
          title={item.label}
          onClick={() => { setActive(item.id); onToggleSidebar() }}
        >
          {item.icon}
        </button>
      ))}
      <div style={{ flex: 1 }} />
      <button
        className="activity-item"
        title="Toggle Panel"
        onClick={onToggleBottom}
      >
        ⊟
      </button>
    </div>
  )
}
