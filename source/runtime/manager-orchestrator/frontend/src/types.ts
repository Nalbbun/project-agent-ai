export type Project = {
  id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
};

export type User = {
  id: string;
  username: string;
  display_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: User;
};

export type Agent = {
  id: string;
  code: string;
  name: string;
  role: string;
  endpoint: string;
  model: string;
  adapter?: string | null;
  prompt_key: string;
  transport: string;
  router_role: string;
  request_timeout_seconds: number;
  max_retries: number;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type Approval = {
  id: string;
  run_id: string;
  step_id?: string | null;
  phase: string;
  status: string;
  required_role: string;
  stage_index: number;
  stage_total: number;
  requested_by_user_id?: string | null;
  decided_by_user_id?: string | null;
  note?: string | null;
  decision_at?: string | null;
  created_at: string;
  due_at?: string | null;
  alerted_at?: string | null;
};

export type ApprovalInboxItem = Approval & {
  run_title: string;
  project_id?: string | null;
  project_name?: string | null;
  actionable: boolean;
  waiting_reason?: string | null;
  is_overdue: boolean;
  due_soon: boolean;
  sla_minutes_remaining?: number | null;
};

export type ApprovalInboxSnapshot = {
  items: ApprovalInboxItem[];
  actionable_count: number;
  queued_count: number;
  total_count: number;
  overdue_count: number;
  due_soon_count: number;
  by_phase: Record<string, number>;
  by_project: Record<string, number>;
};

export type ApprovalAlertItem = {
  id: string;
  run_id: string;
  phase: string;
  project_name?: string | null;
  run_title?: string | null;
  required_role: string;
  due_at?: string | null;
  severity: string;
  sla_minutes_remaining?: number | null;
};

export type ApprovalAlertSnapshot = {
  items: ApprovalAlertItem[];
  overdue_count: number;
  due_soon_count: number;
};

export type WorkerStatus = {
  id: string;
  worker_id: string;
  hostname: string;
  pid: number;
  status: string;
  current_run_id?: string | null;
  current_step_phase?: string | null;
  last_seen_at: string;
  details?: Record<string, unknown> | null;
  created_at: string;
};

export type ProjectMembership = {
  id: string;
  project_id: string;
  user_id: string;
  access_role: string;
  granted_by_user_id?: string | null;
  created_at: string;
};

export type ProjectMembershipInvite = {
  id: string;
  project_id: string;
  invited_user_id: string;
  access_role: string;
  status: string;
  invited_by_user_id?: string | null;
  note?: string | null;
  responded_at?: string | null;
  created_at: string;
};

export type ProjectAccessRequest = {
  id: string;
  project_id: string;
  requested_by_user_id: string;
  requested_role: string;
  status: string;
  reviewed_by_user_id?: string | null;
  note?: string | null;
  reviewed_at?: string | null;
  created_at: string;
};

export type RunStep = {
  id: string;
  seq: number;
  phase: string;
  agent_code: string;
  status: string;
  prompt_text?: string | null;
  output_text?: string | null;
  input_payload?: Record<string, unknown> | null;
  output_payload?: Record<string, unknown> | null;
  error_message?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  retry_count: number;
  max_retry_count: number;
  backend_name?: string | null;
  target_model?: string | null;
  schema_valid?: boolean | null;
  execution_ms?: number | null;
  last_attempt_at?: string | null;
  failure_category?: string | null;
  created_at: string;
};

export type RunEvent = {
  id: string;
  run_id: string;
  step_id?: string | null;
  level: string;
  event_type: string;
  message: string;
  trace_id?: string | null;
  request_id?: string | null;
  payload?: Record<string, unknown> | null;
  created_at: string;
};

export type Artifact = {
  id: string;
  run_id: string;
  step_id?: string | null;
  artifact_type: string;
  name: string;
  storage_type: string;
  path?: string | null;
  content_type?: string | null;
  summary?: string | null;
  content?: Record<string, unknown> | null;
  created_at: string;
};

export type Run = {
  id: string;
  project_id?: string | null;
  title: string;
  user_request: string;
  status: string;
  current_stage?: string | null;
  execution_mode: string;
  queue_status?: string | null;
  final_summary?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  last_error?: string | null;
  run_metadata?: Record<string, unknown> | null;
  next_attempt_at?: string | null;
  queue_attempt_count: number;
  queue_owner?: string | null;
  waiting_reason?: string | null;
  created_at: string;
  updated_at: string;
  steps: RunStep[];
  events: RunEvent[];
  artifacts: Artifact[];
  approvals: Approval[];
};

export type RunEnqueueResponse = {
  run_id: string;
  status: string;
  queue_status: string;
  message: string;
};

export type DashboardProjectApprovalStat = {
  project_id?: string | null;
  project_name: string;
  waiting_approval_count: number;
  overdue_approval_count: number;
  pending_invite_count: number;
  pending_request_count: number;
};

export type DashboardSummary = {
  project_count: number;
  agent_count: number;
  run_count: number;
  running_count: number;
  completed_count: number;
  blocked_count: number;
  dead_lettered_count: number;
  waiting_approval_count: number;
  worker_count: number;
  active_worker_count: number;
  actionable_approval_count: number;
  queued_approval_count: number;
  overdue_approval_count: number;
  due_soon_approval_count: number;
  pending_invite_count: number;
  pending_request_count: number;
  latest_runs: Run[];
  approval_alerts?: ApprovalAlertSnapshot | null;
  project_hotspots: DashboardProjectApprovalStat[];
};

export type FoundationGuardItem = {
  code: string;
  title: string;
  status: 'pass' | 'warn' | 'fail';
  summary: string;
  evidence: Record<string, unknown>;
  required: boolean;
};

export type FoundationGuardSnapshot = {
  status: 'pass' | 'warn' | 'fail';
  generated_at: string;
  items: FoundationGuardItem[];
  warnings: string[];
};

export type ProjectKnowledge = {
  id: string;
  project_id: string;
  title: string;
  source_type: string;
  tags?: string[];
  content: string;
  summary?: string;
  created_at: string;
  updated_at: string;
};

export type WorkerMaintenanceResult = {
  reclaimed_runs: number;
  dead_lettered_runs: number;
};

export type ReplayAudit = {
  id: string;
  run_id: string;
  requested_by_user_id?: string | null;
  mode: string;
  from_phase?: string | null;
  target_seq: number;
  target_phase?: string | null;
  note?: string | null;
  previous_status?: string | null;
  previous_queue_status?: string | null;
  result_status?: string | null;
  result_queue_status?: string | null;
  replay_group?: string | null;
  details?: Record<string, unknown> | null;
  created_at: string;
};

export type ReplayDiff = {
  audit_id: string;
  run_id: string;
  target_phase?: string | null;
  target_seq: number;
  summary: Record<string, unknown>;
  before_steps: Array<Record<string, unknown>>;
  after_steps: Array<Record<string, unknown>>;
  removed_approval_ids: string[];
};

export type ProjectSummary = {
  project_id: string;
  knowledge_count: number;
  membership_count: number;
  run_count: number;
  waiting_approval_count: number;
  my_access_role?: string | null;
  pending_invite_count: number;
  pending_request_count: number;
};
