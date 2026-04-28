from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.api.deps import get_accessible_project_ids, get_db_session, require_roles
from app.core.config import get_settings
from app.models.approval import RunApproval
from app.models.project import Project
from app.models.run import OrchestrationRun
from app.models.user_account import UserAccount
from app.schemas.approval import (
    ApprovalAlertItem,
    ApprovalAlertSnapshot,
    ApprovalDecisionRequest,
    ApprovalInboxItem,
    ApprovalInboxSnapshot,
    ApprovalRead,
)
from app.services.approval_service import ApprovalService

settings = get_settings()
router = APIRouter(tags=["approvals"])


def _approval_sla_state(approval: RunApproval) -> tuple[bool, bool, int | None]:
    if not approval.due_at:
        return False, False, None
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    due = approval.due_at.replace(tzinfo=timezone.utc) if approval.due_at.tzinfo is None else approval.due_at.astimezone(timezone.utc)
    minutes = int((due - now).total_seconds() // 60)
    is_overdue = minutes < 0
    due_soon = not is_overdue and minutes <= settings.approval_alert_before_minutes
    return is_overdue, due_soon, minutes


def _allowed_projects(session: Session, user: UserAccount) -> set:
    return set() if user.role == "admin" else set(get_accessible_project_ids(session, user, "viewer"))


def _build_inbox(session: Session, user: UserAccount) -> ApprovalInboxSnapshot:
    approvals = session.exec(select(RunApproval).where(RunApproval.status.in_(["pending", "queued"])).order_by(RunApproval.created_at.asc())).all()
    allowed_projects = _allowed_projects(session, user)
    items: list[ApprovalInboxItem] = []
    by_phase: dict[str, int] = {}
    by_project: dict[str, int] = {}
    overdue_count = 0
    due_soon_count = 0
    for approval in approvals:
        run = session.get(OrchestrationRun, approval.run_id)
        if not run:
            continue
        if user.role != "admin" and run.project_id and run.project_id not in allowed_projects:
            continue
        project = session.get(Project, run.project_id) if run.project_id else None
        actionable = approval.status == "pending" and (user.role == "admin" or user.role == approval.required_role)
        is_overdue, due_soon, minutes = _approval_sla_state(approval)
        overdue_count += 1 if is_overdue else 0
        due_soon_count += 1 if due_soon else 0
        by_phase[approval.phase] = by_phase.get(approval.phase, 0) + 1
        project_key = project.name if project else "(no-project)"
        by_project[project_key] = by_project.get(project_key, 0) + 1
        items.append(ApprovalInboxItem(
            id=approval.id,
            run_id=approval.run_id,
            step_id=approval.step_id,
            phase=approval.phase,
            status=approval.status,
            required_role=approval.required_role,
            stage_index=approval.stage_index,
            stage_total=approval.stage_total,
            requested_by_user_id=approval.requested_by_user_id,
            decided_by_user_id=approval.decided_by_user_id,
            note=approval.note,
            decision_at=approval.decision_at,
            created_at=approval.created_at,
            due_at=approval.due_at,
            alerted_at=approval.alerted_at,
            run_title=run.title,
            project_id=run.project_id,
            project_name=project.name if project else None,
            actionable=actionable,
            waiting_reason=run.waiting_reason,
            is_overdue=is_overdue,
            due_soon=due_soon,
            sla_minutes_remaining=minutes,
        ))
    return ApprovalInboxSnapshot(
        items=items,
        actionable_count=sum(1 for item in items if item.actionable),
        queued_count=sum(1 for item in items if not item.actionable),
        total_count=len(items),
        overdue_count=overdue_count,
        due_soon_count=due_soon_count,
        by_phase=by_phase,
        by_project=by_project,
    )


def _build_alerts(session: Session, user: UserAccount) -> ApprovalAlertSnapshot:
    snapshot = _build_inbox(session, user)
    items: list[ApprovalAlertItem] = []
    for item in snapshot.items:
        if item.is_overdue or item.due_soon:
            items.append(ApprovalAlertItem(
                id=item.id,
                run_id=item.run_id,
                phase=item.phase,
                project_name=item.project_name,
                run_title=item.run_title,
                required_role=item.required_role,
                due_at=item.due_at,
                severity="critical" if item.is_overdue else "warning",
                sla_minutes_remaining=item.sla_minutes_remaining,
            ))
    return ApprovalAlertSnapshot(items=items[:20], overdue_count=snapshot.overdue_count, due_soon_count=snapshot.due_soon_count)


@router.get("/runs/{run_id}/approvals", response_model=list[ApprovalRead])
def list_approvals(run_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer"))) -> list[ApprovalRead]:
    run = session.get(OrchestrationRun, UUID(run_id))
    if not run:
        return []
    if run.project_id and user.role != "admin":
        allowed_projects = _allowed_projects(session, user)
        if run.project_id not in allowed_projects:
            return []
    rows = ApprovalService(session).list_for_run(UUID(run_id))
    return [ApprovalRead.model_validate(row, from_attributes=True) for row in rows]


@router.get("/approvals/inbox", response_model=list[ApprovalInboxItem])
def list_approval_inbox(session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer"))) -> list[ApprovalInboxItem]:
    return _build_inbox(session, user).items


@router.get("/approvals/inbox/stream")
async def stream_approval_inbox(session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer"))):
    async def event_generator():
        last_payload = None
        while True:
            with Session(session.bind) as stream_session:
                payload = _build_inbox(stream_session, user).model_dump(mode="json")
                dumped = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                if dumped != last_payload:
                    yield f"event: snapshot\ndata: {dumped}\n\n"
                    last_payload = dumped
            await asyncio.sleep(settings.event_stream_poll_interval_seconds)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/approvals/alerts", response_model=ApprovalAlertSnapshot)
def approval_alerts(session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer"))) -> ApprovalAlertSnapshot:
    return _build_alerts(session, user)


@router.post("/runs/{run_id}/approvals/{approval_id}/approve", response_model=ApprovalRead)
def approve(run_id: str, approval_id: str, body: ApprovalDecisionRequest, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer"))) -> ApprovalRead:
    row = ApprovalService(session).decide(UUID(run_id), UUID(approval_id), user, "approved", body.note)
    return ApprovalRead.model_validate(row, from_attributes=True)


@router.post("/runs/{run_id}/approvals/{approval_id}/reject", response_model=ApprovalRead)
def reject(run_id: str, approval_id: str, body: ApprovalDecisionRequest, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer"))) -> ApprovalRead:
    row = ApprovalService(session).decide(UUID(run_id), UUID(approval_id), user, "rejected", body.note)
    return ApprovalRead.model_validate(row, from_attributes=True)
