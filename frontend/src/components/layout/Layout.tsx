import { useState, useEffect } from 'react'
import { Outlet } from '@tanstack/react-router'
import { ActivityBar } from './ActivityBar'
import { Sidebar } from './Sidebar'
import { BottomPanel } from './BottomPanel'
import { StatusBar } from './StatusBar'
import { CommandPalette } from '../common/CommandPalette'
import '../../styles/theme.css'
import './Layout.css'

export function Layout() {
  const [sidebarVisible, setSidebarVisible] = useState(true)
  const [bottomVisible, setBottomVisible] = useState(true)
  const [paletteOpen, setPaletteOpen] = useState(false)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'p') {
        e.preventDefault()
        setPaletteOpen(v => !v)
      }
      if (e.ctrlKey && e.key === 'e') {
        e.preventDefault()
        setSidebarVisible(v => !v)
      }
      if (e.ctrlKey && e.key === 'b') {
        e.preventDefault()
        setBottomVisible(v => !v)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <div className="layout">
      <StatusBar />
      <div className="layout-body">
        <ActivityBar
          onToggleSidebar={() => setSidebarVisible(v => !v)}
          onToggleBottom={() => setBottomVisible(v => !v)}
        />
        {sidebarVisible && <Sidebar />}
        <div className="layout-main">
          <div className="layout-center"><Outlet /></div>
          {bottomVisible && <BottomPanel />}
        </div>
      </div>
      <div className="layout-footer">
        <span>Ctrl+E: sidebar · Ctrl+B: panel · Ctrl+P: palette</span>
        <span>Stitch WebUI</span>
      </div>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  )
}
