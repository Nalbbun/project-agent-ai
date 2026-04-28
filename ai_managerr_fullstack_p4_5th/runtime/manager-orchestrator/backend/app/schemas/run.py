from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.approval import ApprovalRead, ApprovalAlertSnapshot
from app.schemas.common import EventRead


class RunCreate(BaseModel):
    project_id: Optional[UUID] = None
    title: str = Field(min_length=2, max_length=160)
    user_request: str = Field(min_length=5)
    execution_mode: str = Field(default="background")


class StepRetryRequest(BaseModel):
    mode: str = Field(default="from-step")


class DeadLetterReplayRequest(BaseModel):
    mode: str = Field(default="from-last-failed")
    from_phase: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=500)


class ArtifactRead(BaseModel):
    id: UUID
    run_id: UUID
    step_id: Optional[UUID] = None
    artifact_type: str
    name: str
    storage_type: str
    path: Optional[str] = None
    content_type: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[dict[str, Any]] = None
    created_at: datetime


class StepRead(BaseModel):
    id: UUID
    seq: int
    phase: str
    agent_code: str
    status: str
    prompt_text: Optional[str] = None
    output_text: Optional[str] = None
    input_payload: Optional[dict[str, Any]] = None
    output_payload: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    retry_count: int = 0
    max_retry_count: int = 0
    backend_name: Optional[str] = None
    target_model: Optional[str] = None
    schema_valid: Optional[bool] = None
    execution_ms: Optional[int] = None
    last_attempt_at: Optional[datetime] = None
    failure_category: Optional[str] = None
    created_at: datetime


class RunRead(BaseModel):
    id: UUID
    project_id: Optional[UUID] = None
    title: str
    user_request: str
    status: str
    current_stage: Optional[str] = None
    execution_mode: str
    queue_status: Optional[str] = None
    final_summary: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    last_error: Optional[str] = None
    run_metadata: Optional[dict[str, Any]] = None
    next_attempt_at: Optional[datetime] = None
    queue_attempt_count: int = 0
    queue_owner: Optional[str] = None
    waiting_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    steps: list[StepRead] = []
    events: list[EventRead] = []
    artifacts: list[ArtifactRead] = []
    approvals: list[ApprovalRead] = []


class RunEnqueueResponse(BaseModel):
    run_id: UUID
    status: str
    queue_status: str
    message: str


class DashboardProjectApprovalStat(BaseModel):
    project_id: UUID | None = None
    project_name: str
    waiting_approval_count: int = 0
    overdue_approval_count: int = 0
    pending_invite_count: int = 0
    pending_request_count: int = 0


class DashboardSummary(BaseModel):
    project_count: int
    agent_count: int
    run_count: int
    running_count: int
    completed_count: int
    blocked_count: int = 0
    dead_lettered_count: int = 0
    waiting_approval_count: int = 0
    worker_count: int = 0
    active_worker_count: int = 0
    actionable_approval_count: int = 0
    queued_approval_count: int = 0
    overdue_approval_count: int = 0
    due_soon_approval_count: int = 0
    pending_invite_count: int = 0
    pending_request_count: int = 0
    latest_runs: list[RunRead]
    approval_alerts: ApprovalAlertSnapshot | None = None
    project_hotspots: list[DashboardProjectApprovalStat] = []


class ReplayAuditRead(BaseModel):
    id: UUID
    run_id: UUID
    requested_by_user_id: Optional[UUID] = None
    mode: str
    from_phase: Optional[str] = None
    target_seq: int
    target_phase: Optional[str] = None
    note: Optional[str] = None
    previous_status: Optional[str] = None
    previous_queue_status: Optional[str] = None
    result_status: Optional[str] = None
    result_queue_status: Optional[str] = None
    replay_group: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    created_at: datetime


class ReplayDiffRead(BaseModel):
    audit_id: UUID
    run_id: UUID
    target_phase: Optional[str] = None
    target_seq: int
    summary: dict[str, Any]
    before_steps: list[dict[str, Any]] = []
    after_steps: list[dict[str, Any]] = []
    removed_approval_ids: list[str] = []
