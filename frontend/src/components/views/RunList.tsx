import { Link } from '@tanstack/react-router'
import { useRuns } from '../../api/hooks'
import { StatusBadge } from '../common/StatusBadge'

export function RunList() {
  const { data: runs, isLoading } = useRuns()

  if (isLoading) return <div className="loading">Loading runs...</div>
  if (!runs?.length) return <div className="empty">No runs found.</div>

  return (
    <div>
      <h1>Runs ({runs.length})</h1>
      <table className="data-table">
        <thead>
          <tr><th>Run ID</th><th>Status</th><th>Description</th></tr>
        </thead>
        <tbody>
          {runs.map(run => (
            <tr key={run.run_id}>
              <td>
                <Link to="/runs/$runId" params={{ runId: run.run_id }}>
                  {run.run_id}
                </Link>
              </td>
              <td><StatusBadge status={run.status} /></td>
              <td>{run.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
