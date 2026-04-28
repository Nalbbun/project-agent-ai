from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field

from app.models.common import TimestampedModel


class ProjectMembershipInvite(TimestampedModel, table=True):
    __tablename__ = "project_membership_invite"

    project_id: uuid.UUID = Field(foreign_key="project.id", index=True)
    invited_user_id: uuid.UUID = Field(foreign_key="user_account.id", index=True)
    access_role: str = Field(default="viewer", max_length=30)
    status: str = Field(default="pending", max_length=30)
    invited_by_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user_account.id")
    note: Optional[str] = None
    responded_at: Optional[datetime] = None
