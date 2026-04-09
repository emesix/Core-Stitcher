import { useDevices } from '../../api/hooks'
import './Sidebar.css'

export function Sidebar() {
  const { data: devices, isLoading } = useDevices()

  return (
    <div className="sidebar">
      <div className="sidebar-label">EXPLORER</div>
      {isLoading ? (
        <div className="sidebar-item dim">Loading...</div>
      ) : devices?.length ? (
        devices.map(dev => (
          <a key={dev.id || dev.name} href={`#/devices/${dev.id || dev.name}`} className="sidebar-item">
            <span className="device-type">{dev.type?.[0] || '?'}</span>
            {dev.name}
          </a>
        ))
      ) : (
        <div className="sidebar-item dim">No devices</div>
      )}
    </div>
  )
}
