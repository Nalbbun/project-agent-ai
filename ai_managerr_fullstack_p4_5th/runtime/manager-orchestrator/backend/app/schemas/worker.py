from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class WorkerRead(BaseModel):
    id: UUID
    worker_id: str
    hostname: str
    pid: int
    status: str
    current_run_id: Optional[UUID] = None
    current_step_phase: Optional[str] = None
    last_seen_at: datetime
    details: dict | None = None
    created_at: datetime


class WorkerMaintenanceResult(BaseModel):
    reclaimed_runs: int = 0
    dead_lettered_runs: int = 0
