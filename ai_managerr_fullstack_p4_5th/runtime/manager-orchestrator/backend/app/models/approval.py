from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import Field

from app.models.common import TimestampedModel


class RunApproval(TimestampedModel, table=True):
    __tablename__ = "run_approval"

    run_id: uuid.UUID = Field(foreign_key="orchestration_run.id", index=True)
    step_id: Optional[uuid.UUID] = Field(default=None, foreign_key="orchestration_step.id")
    phase: str = Field(max_length=60)
    status: str = Field(default="pending", max_length=30)
    required_role: str = Field(default="reviewer", max_length=30)
    stage_index: int = Field(default=1)
    stage_total: int = Field(default=1)
    requested_by_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user_account.id")
    decided_by_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user_account.id")
    note: Optional[str] = Field(default=None, sa_column=Column(Text))
    decision_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    alerted_at: Optional[datetime] = None
