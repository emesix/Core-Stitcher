import './StatusBar.css'

export function StatusBar() {
  return (
    <div className="status-bar">
      <span className="status-profile">lab @ localhost</span>
      <span className="status-connection" style={{ color: '#4ade80' }}>● connected</span>
    </div>
  )
}
