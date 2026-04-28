from __future__ import annotations

import os
import socket
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.run import OrchestrationRun
from app.models.worker_heartbeat import WorkerHeartbeat

settings = get_settings()


class WorkerService:
    def __init__(self, session: Session, worker_id: str | None = None):
        self.session = session
        self.worker_id = worker_id or settings.worker_id or f"{socket.gethostname()}-{os.getpid()}"

    def heartbeat(self, status: str = "idle", current_run_id=None, current_step_phase=None, details=None) -> WorkerHeartbeat:
        worker = self.session.exec(select(WorkerHeartbeat).where(WorkerHeartbeat.worker_id == self.worker_id)).first()
        if not worker:
            worker = WorkerHeartbeat(
                worker_id=self.worker_id,
                hostname=socket.gethostname(),
                pid=os.getpid(),
                status=status,
                current_run_id=current_run_id,
                current_step_phase=current_step_phase,
                last_seen_at=datetime.utcnow(),
                details=details,
            )
        else:
            worker.status = status
            worker.current_run_id = current_run_id
            worker.current_step_phase = current_step_phase
            worker.last_seen_at = datetime.utcnow()
            worker.details = details
            worker.hostname = socket.gethostname()
            worker.pid = os.getpid()
        self.session.add(worker)
        self.session.commit()
        self.session.refresh(worker)
        return worker

    def list_workers(self) -> list[WorkerHeartbeat]:
        return self.session.exec(select(WorkerHeartbeat).order_by(WorkerHeartbeat.worker_id.asc())).all()

    def summarize(self) -> dict:
        now = datetime.utcnow()
        workers = self.list_workers()
        stale_cutoff = now - timedelta(seconds=settings.worker_stale_after_seconds)
        stale_runs = self.session.exec(
            select(OrchestrationRun)
            .where(OrchestrationRun.queue_status == "running")
            .where(OrchestrationRun.updated_at < now - timedelta(seconds=settings.run_stale_after_seconds))
        ).all()
        return {
            "worker_count": len(workers),
            "active_worker_count": sum(1 for w in workers if w.last_seen_at >= stale_cutoff),
            "stale_worker_count": sum(1 for w in workers if w.last_seen_at < stale_cutoff),
            "stale_run_count": len(stale_runs),
            "dead_letter_count": sum(1 for r in self.session.exec(select(OrchestrationRun).where(OrchestrationRun.queue_status == "dead_lettered")).all()),
        }
