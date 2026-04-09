import { useState } from 'react'
import './BottomPanel.css'

const TABS = ['Logs', 'Events', 'Steps', 'Notifications']

export function BottomPanel() {
  const [activeTab, setActiveTab] = useState('Logs')

  return (
    <div className="bottom-panel">
      <div className="bottom-tabs">
        {TABS.map(tab => (
          <button
            key={tab}
            className={`bottom-tab ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="bottom-content">
        <div className="dim">No {activeTab.toLowerCase()} yet.</div>
      </div>
    </div>
  )
}
