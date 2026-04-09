import { useDevice, useDeviceNeighbors } from '../../api/hooks'

interface Props { deviceId: string }

export function DeviceDetail({ deviceId }: Props) {
  const { data: device, isLoading } = useDevice(deviceId)
  const { data: neighbors } = useDeviceNeighbors(deviceId)

  if (isLoading) return <div className="loading">Loading...</div>
  if (!device) return <div className="empty">Device not found.</div>

  return (
    <div>
      <h1>{device.name} <span className="dim">{device.type}</span></h1>
      <div className="card">
        <div className="kv"><span className="kv-key">Model</span><span>{device.model || '-'}</span></div>
        <div className="kv"><span className="kv-key">IP</span><span>{device.management_ip || '-'}</span></div>
        <div className="kv"><span className="kv-key">Source</span><span>{device.mcp_source || '-'}</span></div>
      </div>

      {device.ports?.length ? (
        <>
          <h2>Ports ({device.ports.length})</h2>
          <table className="data-table">
            <thead><tr><th>Name</th><th>Type</th><th>Speed</th><th>VLAN</th></tr></thead>
            <tbody>
              {device.ports.map(p => (
                <tr key={p.name}>
                  <td>{p.name}</td>
                  <td>{p.type}</td>
                  <td>{p.speed || '-'}</td>
                  <td>{p.vlans?.mode || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}

      {neighbors?.length ? (
        <>
          <h2>Neighbors ({neighbors.length})</h2>
          <table className="data-table">
            <thead><tr><th>Device</th><th>Local Port</th><th>Remote Port</th></tr></thead>
            <tbody>
              {neighbors.map((n, i) => (
                <tr key={i}>
                  <td><a href={`#/devices/${n.device}`}>{n.device}</a></td>
                  <td>{n.local_port}</td>
                  <td>{n.remote_port}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}

      <p className="back-link"><a href="#/devices">&larr; Back to devices</a></p>
    </div>
  )
}
