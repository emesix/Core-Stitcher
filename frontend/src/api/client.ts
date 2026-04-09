import type {
  Device,
  ImpactResult,
  Neighbor,
  RunRecord,
  StitchError,
  TopologyDiagnostics,
  TraceResult,
  VerificationReport,
} from '../types'

class StitchAPIError extends Error {
  constructor(public error: StitchError) {
    super(error.message)
    this.name = 'StitchAPIError'
  }
}

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({
      code: `http.${resp.status}`,
      message: resp.statusText,
      retryable: resp.status >= 500,
    }))
    throw new StitchAPIError(body as StitchError)
  }
  return resp.json()
}

// ── Queries (GET) ──────────────────────────────────────────
export const api = {
  devices: {
    list: () => fetchJSON<Device[]>('/explorer/devices'),
    get: (id: string) => fetchJSON<Device>(`/explorer/devices/${id}`),
    neighbors: (id: string) => fetchJSON<Neighbor[]>(`/explorer/devices/${id}/neighbors`),
  },
  topology: {
    get: () => fetchJSON<Record<string, unknown>>('/explorer/topology'),
    diagnostics: () => fetchJSON<TopologyDiagnostics>('/explorer/diagnostics'),
  },
  vlans: {
    get: (id: number) => fetchJSON<Record<string, unknown>>(`/explorer/vlans/${id}`),
  },
  runs: {
    list: () => fetchJSON<RunRecord[]>('/runs'),
    get: (id: string) => fetchJSON<RunRecord>(`/runs/${id}`),
  },
  system: {
    health: () => fetchJSON<Record<string, unknown>>('/api/v1/health'),
    info: () => fetchJSON<Record<string, unknown>>('/api/v1/readyz'),
  },

  // ── Commands (POST) ────────────────────────────────────────
  preflight: {
    run: (params?: Record<string, unknown>) =>
      fetchJSON<VerificationReport>('/verify', {
        method: 'POST',
        body: JSON.stringify(params),
      }),
  },
  trace: {
    run: (params: { vlan: number; source: string; target?: string }) =>
      fetchJSON<TraceResult>('/trace', {
        method: 'POST',
        body: JSON.stringify(params),
      }),
  },
  impact: {
    preview: (params: Record<string, unknown>) =>
      fetchJSON<ImpactResult>('/impact', {
        method: 'POST',
        body: JSON.stringify(params),
      }),
  },
  review: {
    approve: (runId: string, comment?: string) =>
      fetchJSON<Record<string, unknown>>(`/runs/${runId}/review`, {
        method: 'POST',
        body: JSON.stringify({ action: 'approve', comment }),
      }),
    reject: (runId: string, comment?: string) =>
      fetchJSON<Record<string, unknown>>(`/runs/${runId}/review`, {
        method: 'POST',
        body: JSON.stringify({ action: 'reject', comment }),
      }),
  },
}

export { StitchAPIError }
