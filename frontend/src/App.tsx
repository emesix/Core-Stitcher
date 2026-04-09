export default function App() {
  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      background: '#1a1a2e',
      color: '#e0e0e0',
      fontFamily: "'SF Mono', 'Fira Code', monospace"
    }}>
      <aside style={{ width: 48, background: '#12122a', borderRight: '1px solid #333' }}>
        {/* Activity rail - Task 4 */}
      </aside>
      <aside style={{ width: 240, background: '#16162e', borderRight: '1px solid #333', padding: 12 }}>
        <div style={{ color: '#7ec8e3', fontWeight: 'bold', marginBottom: 12 }}>EXPLORER</div>
        <div style={{ color: '#888' }}>Loading...</div>
      </aside>
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' as const }}>
        <div style={{ flex: 1, padding: 16 }}>
          <h1 style={{ color: '#7ec8e3', fontSize: '1.3rem' }}>Stitch WebUI</h1>
          <p style={{ color: '#888', marginTop: 8 }}>Operator console ready.</p>
        </div>
        <div style={{
          height: 200,
          background: '#12122a',
          borderTop: '1px solid #444',
          padding: 12
        }}>
          <div style={{ color: '#666', fontSize: '0.85rem' }}>LOGS</div>
          <div style={{ color: '#888', marginTop: 8, fontSize: '0.85rem' }}>No events yet.</div>
        </div>
      </main>
    </div>
  )
}
