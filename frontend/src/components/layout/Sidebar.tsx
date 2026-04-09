import { Link } from '@tanstack/react-router'
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
          <Link
            key={dev.id || dev.name}
            to="/devices/$deviceId"
            params={{ deviceId: dev.id || dev.name }}
            className="sidebar-item"
          >
            <span className="device-type">{dev.type?.[0] || '?'}</span>
            {dev.name}
          </Link>
        ))
      ) : (
        <div className="sidebar-item dim">No devices</div>
      )}
    </div>
  )
}
