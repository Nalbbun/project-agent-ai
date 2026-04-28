from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.models.common import TimestampedModel


class RunReplayAudit(TimestampedModel, table=True):
    __tablename__ = "run_replay_audit"

    run_id: uuid.UUID = Field(foreign_key="orchestration_run.id", index=True)
    requested_by_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user_account.id")
    mode: str = Field(max_length=40)
    from_phase: Optional[str] = Field(default=None, max_length=60)
    target_seq: int = Field(default=1)
    target_phase: Optional[str] = Field(default=None, max_length=60)
    note: Optional[str] = Field(default=None, sa_column=Column(Text))
    previous_status: Optional[str] = Field(default=None, max_length=30)
    previous_queue_status: Optional[str] = Field(default=None, max_length=30)
    result_status: Optional[str] = Field(default=None, max_length=30)
    result_queue_status: Optional[str] = Field(default=None, max_length=30)
    replay_group: Optional[str] = Field(default=None, max_length=120)
    details: Optional[dict] = Field(default=None, sa_column=Column(JSONB, nullable=True))
