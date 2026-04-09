import { useState } from 'react'
import { ActivityBar } from './ActivityBar'
import { Sidebar } from './Sidebar'
import { BottomPanel } from './BottomPanel'
import { StatusBar } from './StatusBar'
import '../../styles/theme.css'
import './Layout.css'

interface LayoutProps {
  children: React.ReactNode
}

export function Layout({ children }: LayoutProps) {
  const [sidebarVisible, setSidebarVisible] = useState(true)
  const [bottomVisible, setBottomVisible] = useState(true)

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
          <div className="layout-center">{children}</div>
          {bottomVisible && <BottomPanel />}
        </div>
      </div>
      <div className="layout-footer">
        <span>Ctrl+E: sidebar · Ctrl+B: panel · Ctrl+P: palette</span>
        <span>Stitch WebUI</span>
      </div>
    </div>
  )
}
