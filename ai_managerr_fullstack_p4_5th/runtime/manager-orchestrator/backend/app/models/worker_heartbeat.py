from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.models.common import TimestampedModel


class WorkerHeartbeat(TimestampedModel, table=True):
    __tablename__ = "worker_heartbeat"

    worker_id: str = Field(index=True, unique=True, max_length=120)
    hostname: str = Field(max_length=120)
    pid: int
    status: str = Field(default="idle", max_length=30)
    current_run_id: Optional[uuid.UUID] = Field(default=None, foreign_key="orchestration_run.id")
    current_step_phase: Optional[str] = Field(default=None, max_length=60)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    details: Optional[dict] = Field(default=None, sa_column=Column(JSONB, nullable=True))
