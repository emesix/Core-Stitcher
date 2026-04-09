// ── Lifecycle ──────────────────────────────────────────────
export type LifecycleState =
  | 'pending' | 'queued' | 'running'
  | 'succeeded' | 'failed' | 'cancelled' | 'timed_out'

export const TERMINAL_STATES: Set<LifecycleState> = new Set([
  'succeeded', 'failed', 'cancelled', 'timed_out'
])

// ── Resources ──────────────────────────────────────────────
export interface Resource {
  uri: string
  type: string
  display_name: string
  summary: string
  status?: LifecycleState
  parent?: string
  children_hint?: number
}

// ── Query ──────────────────────────────────────────────────
export type FilterOp = '=' | '!=' | '>' | '>=' | '<' | '<=' | '~' | 'in'

export interface Filter {
  field: string
  op: FilterOp
  value: string | string[]
}

export interface QueryResult<T = Record<string, unknown>> {
  items: T[]
  total?: number
  next_cursor?: string
}

// ── Commands ───────────────────────────────────────────────
export type CommandSource = 'cli' | 'tui' | 'web' | 'lite' | 'desktop' | 'api' | 'script' | 'internal'
export type ExecutionMode = 'sync' | 'async'
export type RiskLevel = 'low' | 'medium' | 'high'

export interface Command {
  action: string
  target?: string
  params: Record<string, unknown>
  source: CommandSource
  correlation_id: string
  idempotency_key?: string
}

// ── Streams ────────────────────────────────────────────────
export type StreamTopic =
  | 'run.progress' | 'run.log' | 'task.status'
  | 'review.verdict' | 'module.health'
  | 'topology.change' | 'system.event'

export interface StreamEvent {
  event_id: string
  sequence: number
  topic: StreamTopic
  resource: string
  payload: Record<string, unknown>
  timestamp: string
  correlation_id?: string
}

// ── Errors ─────────────────────────────────────────────────
export interface StitchError {
  code: string
  message: string
  retryable: boolean
  detail?: Record<string, unknown>
  correlation_id?: string
  field_errors?: FieldError[]
}

export interface FieldError {
  field: string
  code: string
  message: string
}

// ── Domain types ───────────────────────────────────────────
export interface Device {
  id: string
  name: string
  type: string
  model?: string
  management_ip?: string
  mcp_source?: string
  ports?: Port[]
  children?: Device[]
}

export interface Port {
  name: string
  type: string
  device_name?: string
  speed?: string
  mac?: string
  description?: string
  vlans?: VlanMembership
  expected_neighbor?: ExpectedNeighbor
}

export interface VlanMembership {
  mode: 'TRUNK' | 'ACCESS'
  native?: number
  tagged?: number[]
  access_vlan?: number
}

export interface ExpectedNeighbor {
  device: string
  port: string
  mac?: string
}

export interface Neighbor {
  device: string
  local_port: string
  remote_port: string
  link_id?: string
  link_type?: string
}

export interface Link {
  id: string
  type: string
  endpoints: LinkEndpoint[]
}

export interface LinkEndpoint {
  device: string
  port: string
}

// ── Run / Task / Review ────────────────────────────────────
export interface RunRecord {
  run_id: string
  status: LifecycleState
  description: string
  created_at?: string
  updated_at?: string
  tasks?: TaskRecord[]
}

export interface TaskRecord {
  task_id: string
  description: string
  domain?: string
  status: LifecycleState
  priority?: string
}

export type ReviewVerdict = 'approve' | 'request_changes' | 'reject'

export interface ReviewResult {
  review_id?: string
  run_id: string
  verdict?: ReviewVerdict
  reviewer: string
  requires_human: boolean
  findings: ReviewFinding[]
  summary?: string
}

export interface ReviewFinding {
  description: string
  severity: string
  resource?: string
  suggestion?: string
  category?: string
}

// ── Topology ───────────────────────────────────────────────
export interface TopologyDiagnostics {
  dangling_ports: DanglingPort[]
  orphan_devices: string[]
  missing_endpoints: string[]
  total_devices: number
  total_ports: number
  total_links: number
}

export interface DanglingPort {
  device: string
  port: string
  reason: string
}

// ── Verification ───────────────────────────────────────────
export interface VerificationReport {
  timestamp: string
  results: LinkVerification[]
  summary: VerificationSummary
}

export interface LinkVerification {
  link: string
  link_type: string
  status: string
  highest_severity: string
  checks: CheckResult[]
}

export interface CheckResult {
  check: string
  port: string
  expected?: string
  observed?: string
  source?: string
  flag: string
  message: string
  category?: string
  severity: string
}

export interface VerificationSummary {
  total: number
  ok: number
  warning: number
  error: number
}

// ── Trace ──────────────────────────────────────────────────
export interface TraceResult {
  vlan: number
  source: string
  target?: string
  status: string
  hops: TraceHop[]
  first_break?: BreakPoint
}

export interface TraceHop {
  device: string
  port: string
  link?: string
  status: string
  source?: string
  reason?: string
}

export interface BreakPoint {
  device: string
  port: string
  reason: string
  likely_causes?: string[]
}

// ── Impact ─────────────────────────────────────────────────
export interface ImpactResult {
  proposed_change: string
  impact: ImpactEffect[]
  risk: string
  safe_to_apply: boolean
  highest_severity: string
}

export interface ImpactEffect {
  device: string
  port: string
  effect: string
  severity: string
}

// ── Status helpers ─────────────────────────────────────────
export function statusColor(status: string): string {
  const map: Record<string, string> = {
    succeeded: '#4ade80', ok: '#4ade80', healthy: '#4ade80',
    failed: '#ef4444', error: '#ef4444', timed_out: '#ef4444',
    running: '#facc15',
    warning: '#f97316', degraded: '#f97316',
    pending: '#666', queued: '#666', cancelled: '#666',
  }
  return map[status.toLowerCase()] ?? '#666'
}

export function statusSymbol(status: string): string {
  const map: Record<string, string> = {
    succeeded: '\u2713', ok: '\u2713', healthy: '\u2713',
    failed: '\u2717', error: '\u2717', timed_out: '\u2717',
    running: '\u25cf', warning: '\u25cf', degraded: '\u25cf',
    pending: '\u25cb', queued: '\u25cb', cancelled: '\u2014',
  }
  return map[status.toLowerCase()] ?? '?'
}
