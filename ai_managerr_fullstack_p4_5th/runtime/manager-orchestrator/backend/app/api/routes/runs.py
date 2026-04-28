from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.api.deps import ensure_project_access, get_accessible_project_ids, get_current_user, get_db_session, require_roles
from app.core.config import get_settings
from app.models.event import OrchestrationEvent
from app.models.run import OrchestrationRun
from app.models.run_replay_audit import RunReplayAudit
from app.models.user_account import UserAccount
from app.schemas.common import EventRead, MessageResponse
from app.schemas.run import DeadLetterReplayRequest, ReplayAuditRead, ReplayDiffRead, RunCreate, RunEnqueueResponse, RunRead, StepRetryRequest
from app.services.orchestrator import OrchestratorService
from app.services.run_reader import build_run_read

settings = get_settings()
router = APIRouter(tags=["runs"])


def _ensure_run_access(session: Session, user: UserAccount, run: OrchestrationRun, minimum_project_role: str = "viewer") -> None:
    if run.project_id:
        ensure_project_access(session, user, run.project_id, minimum_project_role)


@router.get("/runs", response_model=list[RunRead])
def list_runs(session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer"))) -> list[RunRead]:
    runs = session.exec(select(OrchestrationRun).order_by(OrchestrationRun.created_at.desc())).all()
    if user.role != "admin":
        allowed = set(get_accessible_project_ids(session, user, "viewer"))
        runs = [run for run in runs if run.project_id is None or run.project_id in allowed]
    return [build_run_read(session, run) for run in runs]


@router.post("/runs", response_model=RunRead, status_code=status.HTTP_201_CREATED)
def create_run(payload: RunCreate, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator"))) -> RunRead:
    if payload.project_id:
        ensure_project_access(session, user, payload.project_id, "editor")
    svc = OrchestratorService(session)
    run = svc.create_run(payload, requested_by_user_id=user.id)
    return build_run_read(session, run)


@router.get("/runs/{run_id}", response_model=RunRead)
def get_run(run_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer"))) -> RunRead:
    run = session.get(OrchestrationRun, UUID(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    _ensure_run_access(session, user, run, "viewer")
    return build_run_read(session, run)


@router.post("/runs/{run_id}/execute", response_model=RunEnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
def execute_run(run_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator"))) -> RunEnqueueResponse:
    run = session.get(OrchestrationRun, UUID(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    _ensure_run_access(session, user, run, "editor")
    svc = OrchestratorService(session)
    run = svc.enqueue_run(UUID(run_id))
    return RunEnqueueResponse(run_id=run.id, status=run.status, queue_status=run.queue_status, message="Run execution requested")


@router.post("/runs/{run_id}/cancel", response_model=RunRead)
def cancel_run(run_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator"))) -> RunRead:
    run = session.get(OrchestrationRun, UUID(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    _ensure_run_access(session, user, run, "editor")
    svc = OrchestratorService(session)
    run = svc.cancel_run(UUID(run_id))
    return build_run_read(session, run)


@router.post("/runs/{run_id}/resume", response_model=RunEnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
def resume_run(run_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator"))) -> RunEnqueueResponse:
    run = session.get(OrchestrationRun, UUID(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    _ensure_run_access(session, user, run, "editor")
    svc = OrchestratorService(session)
    run = svc.resume_run(UUID(run_id))
    return RunEnqueueResponse(run_id=run.id, status=run.status, queue_status=run.queue_status, message="Run resume requested")


@router.post("/runs/{run_id}/retry", response_model=RunEnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
def retry_run(run_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator"))) -> RunEnqueueResponse:
    run = session.get(OrchestrationRun, UUID(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    _ensure_run_access(session, user, run, "editor")
    svc = OrchestratorService(session)
    run = svc.resume_run(UUID(run_id))
    return RunEnqueueResponse(run_id=run.id, status=run.status, queue_status=run.queue_status, message="Run retry requested")


@router.post("/runs/{run_id}/steps/{step_id}/retry", response_model=RunEnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
def retry_step(run_id: str, step_id: str, body: StepRetryRequest, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator"))) -> RunEnqueueResponse:
    run = session.get(OrchestrationRun, UUID(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    _ensure_run_access(session, user, run, "editor")
    svc = OrchestratorService(session)
    run = svc.retry_step(UUID(run_id), UUID(step_id), body.mode)
    return RunEnqueueResponse(run_id=run.id, status=run.status, queue_status=run.queue_status, message="Step retry requested")


@router.post("/runs/{run_id}/dead-letter/replay", response_model=RunEnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
def replay_dead_letter(run_id: str, body: DeadLetterReplayRequest, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator"))) -> RunEnqueueResponse:
    run = session.get(OrchestrationRun, UUID(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    _ensure_run_access(session, user, run, "editor")
    svc = OrchestratorService(session)
    run = svc.dead_letter_replay(UUID(run_id), mode=body.mode, from_phase=body.from_phase, note=body.note, requested_by_user_id=user.id)
    return RunEnqueueResponse(run_id=run.id, status=run.status, queue_status=run.queue_status, message="Dead-letter replay requested")


@router.get("/runs/{run_id}/replay-history", response_model=list[ReplayAuditRead])
def replay_history(run_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer"))) -> list[ReplayAuditRead]:
    run = session.get(OrchestrationRun, UUID(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    _ensure_run_access(session, user, run, "viewer")
    rows = session.exec(select(RunReplayAudit).where(RunReplayAudit.run_id == run.id).order_by(RunReplayAudit.created_at.desc())).all()
    return [ReplayAuditRead.model_validate(row, from_attributes=True) for row in rows]




@router.get("/runs/{run_id}/replay-history/{audit_id}/diff", response_model=ReplayDiffRead)
def replay_diff(run_id: str, audit_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer"))) -> ReplayDiffRead:
    run = session.get(OrchestrationRun, UUID(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    _ensure_run_access(session, user, run, "viewer")
    audit = session.get(RunReplayAudit, UUID(audit_id))
    if not audit or audit.run_id != run.id:
        raise HTTPException(status_code=404, detail="Replay audit not found")
    details = audit.details or {}
    before_steps = details.get("before_steps", [])
    after_steps = details.get("after_steps", [])
    removed_approval_ids = details.get("removed_approval_ids", [])
    summary = {
        "changed_step_count": len(after_steps),
        "affected_phases": details.get("affected_phases", []),
        "reset_step_ids": details.get("reset_step_ids", []),
        "removed_approval_count": len(removed_approval_ids),
        "target": details.get("target", {"seq": audit.target_seq, "phase": audit.target_phase}),
    }
    return ReplayDiffRead(
        audit_id=audit.id,
        run_id=run.id,
        target_phase=audit.target_phase,
        target_seq=audit.target_seq,
        summary=summary,
        before_steps=before_steps,
        after_steps=after_steps,
        removed_approval_ids=removed_approval_ids,
    )


@router.get("/runs/{run_id}/events", response_model=list[EventRead])
def list_events(run_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer"))) -> list[OrchestrationEvent]:
    run_uuid = UUID(run_id)
    run = session.get(OrchestrationRun, run_uuid)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    _ensure_run_access(session, user, run, "viewer")
    return session.exec(select(OrchestrationEvent).where(OrchestrationEvent.run_id == run_uuid).order_by(OrchestrationEvent.created_at.asc())).all()


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)):
    run_uuid = UUID(run_id)
    run = session.get(OrchestrationRun, run_uuid)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    _ensure_run_access(session, user, run, "viewer")

    async def event_generator():
        last_event_count = -1
        last_updated = None
        while True:
            with Session(session.bind) as stream_session:
                stream_run = stream_session.get(OrchestrationRun, run_uuid)
                if not stream_run:
                    yield "event: end\ndata: {}\n\n"
                    return
                event_count = len(stream_session.exec(select(OrchestrationEvent).where(OrchestrationEvent.run_id == run_uuid)).all())
                updated = stream_run.updated_at.isoformat() if stream_run.updated_at else ""
                if last_event_count != event_count or last_updated != updated:
                    payload = build_run_read(stream_session, stream_run).model_dump(mode="json")
                    yield f"event: snapshot\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    last_event_count = event_count
                    last_updated = updated
                if stream_run.queue_status not in {"queued", "resuming", "running", "retry_scheduled", "waiting_approval"}:
                    yield "event: end\ndata: {}\n\n"
                    return
            await asyncio.sleep(settings.event_stream_poll_interval_seconds)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.delete("/runs/{run_id}", response_model=MessageResponse)
def delete_run(run_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin"))) -> MessageResponse:
    run = session.get(OrchestrationRun, UUID(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    session.delete(run)
    session.commit()
    return MessageResponse(message="Run deleted")
