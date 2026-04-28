from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = None


class ProjectRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ProjectKnowledgeCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    source_type: str = Field(default="note", max_length=40)
    tags: list[str] | None = None
    content: str = Field(min_length=1)
    summary: Optional[str] = None


class ProjectKnowledgeRead(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    source_type: str
    tags: list[str] | None = None
    content: str
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ProjectMembershipCreate(BaseModel):
    user_id: UUID
    access_role: str = Field(default="viewer", max_length=30)


class ProjectMembershipRead(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    access_role: str
    granted_by_user_id: UUID | None = None
    created_at: datetime


class ProjectMembershipInviteCreate(BaseModel):
    invited_user_id: UUID
    access_role: str = Field(default="viewer", max_length=30)
    note: Optional[str] = None


class ProjectMembershipInviteRead(BaseModel):
    id: UUID
    project_id: UUID
    invited_user_id: UUID
    access_role: str
    status: str
    invited_by_user_id: UUID | None = None
    note: Optional[str] = None
    responded_at: datetime | None = None
    created_at: datetime


class ProjectAccessRequestCreate(BaseModel):
    requested_role: str = Field(default="viewer", max_length=30)
    note: Optional[str] = None


class ProjectAccessRequestDecision(BaseModel):
    access_role: str = Field(default="viewer", max_length=30)
    note: Optional[str] = None


class ProjectAccessRequestRead(BaseModel):
    id: UUID
    project_id: UUID
    requested_by_user_id: UUID
    requested_role: str
    status: str
    reviewed_by_user_id: UUID | None = None
    note: Optional[str] = None
    reviewed_at: datetime | None = None
    created_at: datetime


class ProjectSummaryRead(BaseModel):
    project_id: UUID
    knowledge_count: int = 0
    membership_count: int = 0
    run_count: int = 0
    waiting_approval_count: int = 0
    my_access_role: str | None = None
    pending_invite_count: int = 0
    pending_request_count: int = 0
