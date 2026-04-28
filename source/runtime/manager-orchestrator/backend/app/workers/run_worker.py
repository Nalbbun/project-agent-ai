from __future__ import annotations

import time

from sqlmodel import Session

from app.core.config import get_settings
from app.db.session import engine, wait_for_db
from app.services.job_queue import JobQueueService
from app.services.orchestrator import OrchestratorService
from app.services.seed import seed_agents_from_yaml
from app.services.worker_service import WorkerService

settings = get_settings()


def main() -> None:
    wait_for_db()
    seed_agents_from_yaml()
    while True:
        with Session(engine) as session:
            worker = WorkerService(session)
            queue = JobQueueService(session)
            reclaimed = queue.reclaim_stale_runs()
            dead_lettered = queue.dead_letter_exhausted_runs()
            run = queue.claim_next_pending_run(worker.worker_id)
            if run:
                worker.heartbeat(status="processing", current_run_id=run.id, current_step_phase=run.current_stage, details={"queue_status": run.queue_status})
                orchestrator = OrchestratorService(session)
                orchestrator.execute_run_inline(run.id, worker_id=worker.worker_id)
                worker.heartbeat(status="idle", details={"last_run_id": str(run.id), "reclaimed": reclaimed, "dead_lettered": dead_lettered})
            else:
                worker.heartbeat(status="idle", details={"reclaimed": reclaimed, "dead_lettered": dead_lettered})
        time.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    main()
