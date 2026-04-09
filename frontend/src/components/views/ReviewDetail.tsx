import { useState } from 'react'
import { useRun, useReviewApprove, useReviewReject } from '../../api/hooks'
import { StatusBadge } from '../common/StatusBadge'
import type { ReviewFinding } from '../../types'

interface Props { reviewId: string }

export function ReviewDetail({ reviewId }: Props) {
  const { data: run } = useRun(reviewId)
  const approveMutation = useReviewApprove()
  const rejectMutation = useReviewReject()
  const [comment, setComment] = useState('')

  if (!run) return <div className="loading">Loading review...</div>

  const findings: ReviewFinding[] = (run as any).findings || []

  return (
    <div>
      <h1 style={{ color: 'var(--warning)' }}>Review: {run.run_id}</h1>
      <div className="card">
        <StatusBadge status={run.status} />
        <div className="kv">
          <span className="kv-key">Description</span><span>{run.description}</span>
        </div>
      </div>

      {findings.length > 0 && (
        <>
          <h2>Findings ({findings.length})</h2>
          {findings.map((f, i) => (
            <div
              key={i}
              className="card"
              style={{
                borderLeft: `3px solid ${
                  f.severity === 'ERROR'
                    ? 'var(--error)'
                    : f.severity === 'WARNING'
                      ? 'var(--warning)'
                      : 'var(--text-dim)'
                }`,
              }}
            >
              <div>
                <StatusBadge status={f.severity.toLowerCase()} /> {f.description}
              </div>
              {f.suggestion && (
                <div style={{ color: 'var(--accent)', marginTop: 4 }}>
                  Suggestion: {f.suggestion}
                </div>
              )}
            </div>
          ))}
        </>
      )}

      <h2>Actions</h2>
      <div className="card">
        <textarea
          value={comment}
          onChange={e => setComment(e.target.value)}
          placeholder="Comment (optional)"
          style={{
            width: '100%',
            background: 'var(--bg)',
            color: 'var(--text)',
            border: '1px solid var(--border)',
            padding: 8,
            borderRadius: 4,
            fontFamily: 'var(--font-mono)',
            marginBottom: 8,
            resize: 'vertical',
          }}
          rows={2}
        />
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="btn btn-ok"
            onClick={() => approveMutation.mutate({ runId: reviewId, comment })}
            disabled={approveMutation.isPending}
          >
            {approveMutation.isPending ? 'Approving...' : 'Approve'}
          </button>
          <button
            className="btn btn-danger"
            onClick={() => rejectMutation.mutate({ runId: reviewId, comment })}
            disabled={rejectMutation.isPending}
          >
            {rejectMutation.isPending ? 'Rejecting...' : 'Reject'}
          </button>
        </div>
        {approveMutation.isSuccess && (
          <div style={{ color: 'var(--ok)', marginTop: 8 }}>Approved</div>
        )}
        {rejectMutation.isSuccess && (
          <div style={{ color: 'var(--error)', marginTop: 8 }}>Rejected</div>
        )}
      </div>

      <a href="#/runs" className="back-link">&larr; Back to runs</a>
    </div>
  )
}
