import { useRun } from '../../api/hooks'
import { StatusBadge } from '../common/StatusBadge'

interface Props { runId: string }

export function RunDetail({ runId }: Props) {
  const { data: run, isLoading } = useRun(runId)

  if (isLoading) return <div className="loading">Loading run...</div>
  if (!run) return <div className="empty">Run not found.</div>

  const tasks = run.tasks || []
  const completed = tasks.filter(
    t => t.status === 'succeeded' || t.status === 'failed'
  ).length

  return (
    <div>
      <h1>{run.run_id} <StatusBadge status={run.status} /></h1>
      <div className="card">
        <div className="kv">
          <span className="kv-key">Description</span><span>{run.description}</span>
        </div>
        <div className="kv">
          <span className="kv-key">Status</span><span>{run.status}</span>
        </div>
        {tasks.length > 0 && (
          <div className="kv">
            <span className="kv-key">Progress</span>
            <span>{completed}/{tasks.length} tasks</span>
          </div>
        )}
      </div>

      {tasks.length > 0 && (
        <>
          <h2>Tasks</h2>
          <table className="data-table">
            <thead>
              <tr><th>Task ID</th><th>Status</th><th>Description</th></tr>
            </thead>
            <tbody>
              {tasks.map(t => (
                <tr key={t.task_id}>
                  <td>{t.task_id}</td>
                  <td><StatusBadge status={t.status} /></td>
                  <td>{t.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <div className="actions" style={{ marginTop: '1rem' }}>
        <a href="#/runs" className="back-link">&larr; Back to runs</a>
      </div>
    </div>
  )
}
