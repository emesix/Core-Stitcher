import { useDevices } from '../../api/hooks'

export function DeviceList() {
  const { data: devices, isLoading, error } = useDevices()

  if (isLoading) return <div className="loading">Loading devices...</div>
  if (error) return <div className="error">Failed to load devices: {error.message}</div>
  if (!devices?.length) return <div className="empty">No devices found.</div>

  return (
    <div>
      <h1>Devices ({devices.length})</h1>
      <table className="data-table">
        <thead>
          <tr><th>Name</th><th>Type</th><th>Model</th><th>IP</th></tr>
        </thead>
        <tbody>
          {devices.map(dev => (
            <tr key={dev.id || dev.name}>
              <td><a href={`#/devices/${dev.id || dev.name}`}>{dev.name}</a></td>
              <td>{dev.type}</td>
              <td>{dev.model || '-'}</td>
              <td>{dev.management_ip || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
