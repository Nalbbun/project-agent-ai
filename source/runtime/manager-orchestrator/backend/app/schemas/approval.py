from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ApprovalDecisionRequest(BaseModel):
    note: Optional[str] = Field(default=None, max_length=500)


class ApprovalRead(BaseModel):
    id: UUID
    run_id: UUID
    step_id: Optional[UUID] = None
    phase: str
    status: str
    required_role: str
    stage_index: int = 1
    stage_total: int = 1
    requested_by_user_id: Optional[UUID] = None
    decided_by_user_id: Optional[UUID] = None
    note: Optional[str] = None
    decision_at: Optional[datetime] = None
    created_at: datetime
    due_at: Optional[datetime] = None
    alerted_at: Optional[datetime] = None


class ApprovalInboxItem(ApprovalRead):
    run_title: str
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    actionable: bool = False
    waiting_reason: Optional[str] = None
    is_overdue: bool = False
    due_soon: bool = False
    sla_minutes_remaining: Optional[int] = None


class ApprovalInboxSnapshot(BaseModel):
    items: list[ApprovalInboxItem]
    actionable_count: int
    queued_count: int
    total_count: int
    overdue_count: int = 0
    due_soon_count: int = 0
    by_phase: dict[str, int] = {}
    by_project: dict[str, int] = {}


class ApprovalAlertItem(BaseModel):
    id: UUID
    run_id: UUID
    phase: str
    project_name: Optional[str] = None
    run_title: Optional[str] = None
    required_role: str
    due_at: Optional[datetime] = None
    severity: str = "info"
    sla_minutes_remaining: Optional[int] = None


class ApprovalAlertSnapshot(BaseModel):
    items: list[ApprovalAlertItem]
    overdue_count: int = 0
    due_soon_count: int = 0
