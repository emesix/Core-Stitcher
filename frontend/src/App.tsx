import { Layout } from './components/layout/Layout'

export default function App() {
  return (
    <Layout>
      <h1 style={{ color: 'var(--accent)', fontSize: '1.3rem' }}>Stitch WebUI</h1>
      <p style={{ color: 'var(--text-dim)', marginTop: 8 }}>Operator console ready. Select a resource from the sidebar.</p>
    </Layout>
  )
}
