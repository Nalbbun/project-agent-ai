from __future__ import annotations

import uuid
from typing import Optional

from sqlmodel import Field

from app.models.common import TimestampedModel


class ProjectMembership(TimestampedModel, table=True):
    __tablename__ = "project_membership"

    project_id: uuid.UUID = Field(foreign_key="project.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="user_account.id", index=True)
    access_role: str = Field(default="viewer", max_length=30)
    granted_by_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user_account.id")
