from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.run import OrchestrationRun

settings = get_settings()


class JobQueueService:
    def __init__(self, session: Session):
        self.session = session

    def enqueue_run(self, run_id: UUID) -> OrchestrationRun:
        run = self.session.get(OrchestrationRun, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.queue_status == "running":
            return run
        run.queue_status = "queued"
        run.status = "queued"
        run.last_error = None
        run.waiting_reason = None
        run.next_attempt_at = datetime.utcnow()
        run.updated_at = datetime.utcnow()
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def cancel_run(self, run_id: UUID) -> OrchestrationRun:
        run = self.session.get(OrchestrationRun, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        run.queue_status = "cancelled"
        run.status = "cancelled"
        run.updated_at = datetime.utcnow()
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def claim_next_pending_run(self, worker_id: str) -> OrchestrationRun | None:
        now = datetime.utcnow()
        stmt = (
            select(OrchestrationRun)
            .where(OrchestrationRun.queue_status.in_(["queued", "resuming", "retry_scheduled"]))
            .where((OrchestrationRun.next_attempt_at.is_(None)) | (OrchestrationRun.next_attempt_at <= now))
            .order_by(OrchestrationRun.created_at.asc())
        )
        run = self.session.exec(stmt).first()
        if not run:
            return None
        run.queue_status = "running"
        run.status = "running"
        run.queue_owner = worker_id
        run.started_at = run.started_at or now
        run.queue_attempt_count += 1
        run.updated_at = now
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def reclaim_stale_runs(self) -> int:
        cutoff = datetime.utcnow().timestamp() - settings.run_stale_after_seconds
        stale_before = datetime.utcfromtimestamp(cutoff)
        rows = self.session.exec(
            select(OrchestrationRun)
            .where(OrchestrationRun.queue_status == "running")
            .where(OrchestrationRun.updated_at < stale_before)
        ).all()
        count = 0
        for run in rows:
            run.queue_status = "retry_scheduled"
            run.status = "retrying"
            run.queue_owner = None
            run.waiting_reason = "stale_run_reclaimed"
            run.next_attempt_at = datetime.utcnow()
            run.updated_at = datetime.utcnow()
            self.session.add(run)
            count += 1
        self.session.commit()
        return count

    def dead_letter_exhausted_runs(self) -> int:
        rows = self.session.exec(
            select(OrchestrationRun)
            .where(OrchestrationRun.queue_attempt_count >= settings.queue_dead_letter_attempts)
            .where(OrchestrationRun.queue_status.in_(["queued", "retry_scheduled", "running", "resuming"]))
        ).all()
        count = 0
        for run in rows:
            run.queue_status = "dead_lettered"
            run.status = "failed"
            run.waiting_reason = "dead_lettered"
            run.queue_owner = None
            run.updated_at = datetime.utcnow()
            self.session.add(run)
            count += 1
        self.session.commit()
        return count
