from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.api.deps import get_db_session, require_roles
from app.models.user_account import UserAccount
from app.schemas.worker import WorkerMaintenanceResult, WorkerRead
from app.services.job_queue import JobQueueService
from app.services.worker_service import WorkerService
from app.core.config import get_settings

router = APIRouter(tags=["workers"])
settings = get_settings()


def _worker_snapshot(session: Session) -> dict:
    service = WorkerService(session)
    workers = [WorkerRead.model_validate(row, from_attributes=True).model_dump(mode="json") for row in service.list_workers()]
    summary = service.summarize()
    return {"workers": workers, "summary": summary}


@router.get("/workers", response_model=list[WorkerRead])
def list_workers(session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer"))) -> list[WorkerRead]:
    rows = WorkerService(session).list_workers()
    return [WorkerRead.model_validate(row, from_attributes=True) for row in rows]


@router.get("/workers/stream")
async def stream_workers(session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer"))):
    async def event_generator():
        last_payload = None
        while True:
            with Session(session.bind) as stream_session:
                payload = _worker_snapshot(stream_session)
                dumped = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                if dumped != last_payload:
                    yield f"event: snapshot\ndata: {dumped}\n\n"
                    last_payload = dumped
            await asyncio.sleep(settings.event_stream_poll_interval_seconds)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/workers/maintenance", response_model=WorkerMaintenanceResult)
def maintain_workers(session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator"))) -> WorkerMaintenanceResult:
    queue = JobQueueService(session)
    reclaimed = queue.reclaim_stale_runs()
    dead_lettered = queue.dead_letter_exhausted_runs()
    return WorkerMaintenanceResult(reclaimed_runs=reclaimed, dead_lettered_runs=dead_lettered)
