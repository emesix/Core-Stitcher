import { useState, useEffect, useRef } from 'react'
import { useRouter } from '@tanstack/react-router'
import './CommandPalette.css'

const COMMANDS = [
  { label: 'Go to Devices', path: '/devices' },
  { label: 'Go to Runs', path: '/runs' },
  { label: 'Go to Topology', path: '/' },
  { label: 'Run Preflight', path: '/preflight' },
  { label: 'System Health', path: '/system' },
]

interface Props {
  open: boolean
  onClose: () => void
}

export function CommandPalette({ open, onClose }: Props) {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const router = useRouter()

  useEffect(() => {
    if (open) {
      setQuery('')
      setSelected(0)
      inputRef.current?.focus()
    }
  }, [open])

  if (!open) return null

  const filtered = COMMANDS.filter(c =>
    c.label.toLowerCase().includes(query.toLowerCase()),
  )

  const handleSelect = (path: string) => {
    router.navigate({ to: path })
    onClose()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose()
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelected(i => Math.min(i + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelected(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && filtered.length > 0) {
      handleSelect(filtered[selected]!.path)
    }
  }

  return (
    <div className="palette-overlay" onClick={onClose}>
      <div className="palette-container" onClick={e => e.stopPropagation()}>
        <input
          ref={inputRef}
          className="palette-input"
          value={query}
          onChange={e => { setQuery(e.target.value); setSelected(0) }}
          placeholder="Type a command..."
          onKeyDown={handleKeyDown}
        />
        <div className="palette-results">
          {filtered.map((cmd, i) => (
            <button
              key={cmd.path}
              className={`palette-item ${i === selected ? 'selected' : ''}`}
              onClick={() => handleSelect(cmd.path)}
            >
              {cmd.label}
            </button>
          ))}
          {filtered.length === 0 && (
            <div className="palette-empty">No matches</div>
          )}
        </div>
      </div>
    </div>
  )
}
