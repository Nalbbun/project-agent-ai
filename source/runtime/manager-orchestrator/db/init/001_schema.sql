CREATE TABLE IF NOT EXISTS project (
  id UUID PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  description TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_account (
  id UUID PRIMARY KEY,
  username VARCHAR(60) NOT NULL UNIQUE,
  display_name VARCHAR(120) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(30) NOT NULL DEFAULT 'viewer',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auth_session (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
  token VARCHAR(255) NOT NULL UNIQUE,
  expires_at TIMESTAMP NOT NULL,
  last_seen_at TIMESTAMP,
  revoked_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_membership (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
  access_role VARCHAR(30) NOT NULL DEFAULT 'viewer',
  granted_by_user_id UUID REFERENCES user_account(id) ON DELETE SET NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_membership_invite (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  invited_user_id UUID NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
  access_role VARCHAR(30) NOT NULL DEFAULT 'viewer',
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  invited_by_user_id UUID REFERENCES user_account(id) ON DELETE SET NULL,
  note TEXT,
  responded_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_access_request (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  requested_by_user_id UUID NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
  requested_role VARCHAR(30) NOT NULL DEFAULT 'viewer',
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  reviewed_by_user_id UUID REFERENCES user_account(id) ON DELETE SET NULL,
  note TEXT,
  reviewed_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_knowledge (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
  title VARCHAR(160) NOT NULL,
  source_type VARCHAR(40) NOT NULL DEFAULT 'note',
  tags JSONB,
  content TEXT NOT NULL,
  summary TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_catalog (
  id UUID PRIMARY KEY,
  code VARCHAR(40) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  role VARCHAR(40) NOT NULL,
  endpoint VARCHAR(255) NOT NULL,
  model VARCHAR(120) NOT NULL,
  adapter VARCHAR(120),
  prompt_key VARCHAR(60) NOT NULL,
  transport VARCHAR(20) NOT NULL DEFAULT 'router',
  router_role VARCHAR(40) NOT NULL,
  request_timeout_seconds INTEGER NOT NULL DEFAULT 180,
  max_retries INTEGER NOT NULL DEFAULT 2,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orchestration_run (
  id UUID PRIMARY KEY,
  project_id UUID REFERENCES project(id),
  title VARCHAR(160) NOT NULL,
  user_request TEXT NOT NULL,
  status VARCHAR(30) NOT NULL,
  current_stage VARCHAR(60),
  execution_mode VARCHAR(20) NOT NULL DEFAULT 'background',
  queue_status VARCHAR(30) NOT NULL DEFAULT 'pending',
  final_summary TEXT,
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  last_error TEXT,
  run_metadata JSONB,
  next_attempt_at TIMESTAMP,
  queue_attempt_count INTEGER NOT NULL DEFAULT 0,
  queue_owner VARCHAR(120),
  waiting_reason VARCHAR(120),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orchestration_step (
  id UUID PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES orchestration_run(id) ON DELETE CASCADE,
  seq INTEGER NOT NULL,
  phase VARCHAR(60) NOT NULL,
  agent_code VARCHAR(40) NOT NULL,
  status VARCHAR(30) NOT NULL,
  prompt_text TEXT,
  output_text TEXT,
  input_payload JSONB,
  output_payload JSONB,
  error_message TEXT,
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  retry_count INTEGER NOT NULL DEFAULT 0,
  max_retry_count INTEGER NOT NULL DEFAULT 2,
  backend_name VARCHAR(80),
  target_model VARCHAR(120),
  schema_valid BOOLEAN,
  execution_ms INTEGER,
  last_attempt_at TIMESTAMP,
  failure_category VARCHAR(40),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS run_approval (
  id UUID PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES orchestration_run(id) ON DELETE CASCADE,
  step_id UUID REFERENCES orchestration_step(id) ON DELETE SET NULL,
  phase VARCHAR(60) NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  required_role VARCHAR(30) NOT NULL DEFAULT 'reviewer',
  stage_index INTEGER NOT NULL DEFAULT 1,
  stage_total INTEGER NOT NULL DEFAULT 1,
  requested_by_user_id UUID REFERENCES user_account(id) ON DELETE SET NULL,
  decided_by_user_id UUID REFERENCES user_account(id) ON DELETE SET NULL,
  note TEXT,
  decision_at TIMESTAMP,
  due_at TIMESTAMP,
  alerted_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orchestration_event (
  id UUID PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES orchestration_run(id) ON DELETE CASCADE,
  step_id UUID REFERENCES orchestration_step(id) ON DELETE SET NULL,
  level VARCHAR(20) NOT NULL,
  event_type VARCHAR(40) NOT NULL DEFAULT 'log',
  message TEXT NOT NULL,
  trace_id VARCHAR(120),
  request_id VARCHAR(120),
  payload JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS artifact (
  id UUID PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES orchestration_run(id) ON DELETE CASCADE,
  step_id UUID REFERENCES orchestration_step(id) ON DELETE SET NULL,
  artifact_type VARCHAR(40) NOT NULL,
  name VARCHAR(120) NOT NULL,
  storage_type VARCHAR(20) NOT NULL DEFAULT 'json',
  path VARCHAR(255),
  content_type VARCHAR(120),
  summary TEXT,
  content JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS run_replay_audit (
  id UUID PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES orchestration_run(id) ON DELETE CASCADE,
  requested_by_user_id UUID REFERENCES user_account(id) ON DELETE SET NULL,
  mode VARCHAR(40) NOT NULL,
  from_phase VARCHAR(60),
  target_seq INTEGER NOT NULL DEFAULT 1,
  target_phase VARCHAR(60),
  note TEXT,
  previous_status VARCHAR(30),
  previous_queue_status VARCHAR(30),
  result_status VARCHAR(30),
  result_queue_status VARCHAR(30),
  replay_group VARCHAR(120),
  details JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS worker_heartbeat (
  id UUID PRIMARY KEY,
  worker_id VARCHAR(120) NOT NULL UNIQUE,
  hostname VARCHAR(120) NOT NULL,
  pid INTEGER NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'idle',
  current_run_id UUID REFERENCES orchestration_run(id) ON DELETE SET NULL,
  current_step_phase VARCHAR(60),
  last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  details JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_project_membership_project ON project_membership(project_id, user_id);
CREATE INDEX IF NOT EXISTS idx_project_invite_project ON project_membership_invite(project_id, status);
CREATE INDEX IF NOT EXISTS idx_project_request_project ON project_access_request(project_id, status);
CREATE INDEX IF NOT EXISTS idx_orchestration_run_project ON orchestration_run(project_id);
CREATE INDEX IF NOT EXISTS idx_orchestration_run_queue_status ON orchestration_run(queue_status);
CREATE INDEX IF NOT EXISTS idx_orchestration_run_next_attempt ON orchestration_run(next_attempt_at);
CREATE INDEX IF NOT EXISTS idx_orchestration_step_run_seq ON orchestration_step(run_id, seq);
CREATE INDEX IF NOT EXISTS idx_orchestration_event_run ON orchestration_event(run_id, created_at);
CREATE INDEX IF NOT EXISTS idx_artifact_run ON artifact(run_id, created_at);
CREATE INDEX IF NOT EXISTS idx_project_knowledge_project ON project_knowledge(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_run_approval_run ON run_approval(run_id, created_at);
CREATE INDEX IF NOT EXISTS idx_run_approval_due ON run_approval(status, due_at);
CREATE INDEX IF NOT EXISTS idx_auth_session_token ON auth_session(token);
CREATE INDEX IF NOT EXISTS idx_run_replay_audit_run ON run_replay_audit(run_id, created_at);
