import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from './client'

// ── Device hooks ───────────────────────────────────────────
export function useDevices() {
  return useQuery({ queryKey: ['devices'], queryFn: api.devices.list })
}

export function useDevice(id: string) {
  return useQuery({ queryKey: ['device', id], queryFn: () => api.devices.get(id), enabled: !!id })
}

export function useDeviceNeighbors(id: string) {
  return useQuery({
    queryKey: ['device', id, 'neighbors'],
    queryFn: () => api.devices.neighbors(id),
    enabled: !!id,
  })
}

// ── Topology hooks ─────────────────────────────────────────
export function useTopology() {
  return useQuery({ queryKey: ['topology'], queryFn: api.topology.get })
}

export function useTopologyDiagnostics() {
  return useQuery({ queryKey: ['topology', 'diagnostics'], queryFn: api.topology.diagnostics })
}

// ── Run hooks ──────────────────────────────────────────────
export function useRuns() {
  return useQuery({ queryKey: ['runs'], queryFn: api.runs.list })
}

export function useRun(id: string) {
  return useQuery({ queryKey: ['run', id], queryFn: () => api.runs.get(id), enabled: !!id })
}

// ── System hooks ───────────────────────────────────────────
export function useSystemHealth() {
  return useQuery({ queryKey: ['system', 'health'], queryFn: api.system.health })
}

// ── Mutation hooks ─────────────────────────────────────────
export function usePreflightRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (params?: Record<string, unknown>) => api.preflight.run(params),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['runs'] })
    },
  })
}

export function useTraceRun() {
  return useMutation({
    mutationFn: (params: { vlan: number; source: string; target?: string }) =>
      api.trace.run(params),
  })
}

export function useReviewApprove() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ runId, comment }: { runId: string; comment?: string }) =>
      api.review.approve(runId, comment),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['runs'] })
    },
  })
}

export function useReviewReject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ runId, comment }: { runId: string; comment?: string }) =>
      api.review.reject(runId, comment),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['runs'] })
    },
  })
}
