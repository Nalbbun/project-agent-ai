import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.api.deps import get_accessible_project_ids, get_db_session, require_roles
from app.models.agent import AgentCatalog
from app.models.approval import RunApproval
from app.models.project import Project
from app.models.project_access_request import ProjectAccessRequest
from app.models.project_membership_invite import ProjectMembershipInvite
from app.models.run import OrchestrationRun
from app.models.user_account import UserAccount
from app.schemas.approval import ApprovalAlertItem, ApprovalAlertSnapshot
from app.schemas.run import DashboardProjectApprovalStat, DashboardSummary
from app.services.run_reader import build_run_read
from app.services.worker_service import WorkerService
from app.core.config import get_settings

router = APIRouter(tags=["dashboard"])
settings = get_settings()


def _approval_alert_state(approval: RunApproval) -> tuple[bool, bool, int | None]:
    if not approval.due_at:
        return False, False, None
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    due = approval.due_at.replace(tzinfo=timezone.utc) if approval.due_at.tzinfo is None else approval.due_at.astimezone(timezone.utc)
    minutes = int((due - now).total_seconds() // 60)
    overdue = minutes < 0
    due_soon = not overdue and minutes <= settings.approval_alert_before_minutes
    return overdue, due_soon, minutes


def _build_summary(session: Session, user: UserAccount) -> DashboardSummary:
    stmt = select(OrchestrationRun).order_by(OrchestrationRun.created_at.desc())
    if user.role != "admin":
        allowed = get_accessible_project_ids(session, user, "viewer")
        runs = [run for run in session.exec(stmt).all() if (run.project_id is None or run.project_id in allowed)]
        projects = [project for project in session.exec(select(Project)).all() if project.id in allowed]
    else:
        runs = session.exec(stmt).all()
        projects = session.exec(select(Project)).all()
    latest_runs = [build_run_read(session, run) for run in runs[:5]]
    worker_summary = WorkerService(session).summarize()

    project_lookup = {project.id: project for project in projects}
    project_stats: dict[str, DashboardProjectApprovalStat] = {}
    alerts: list[ApprovalAlertItem] = []
    actionable_approval_count = 0
    queued_approval_count = 0
    overdue_approval_count = 0
    due_soon_approval_count = 0
    run_lookup = {run.id: run for run in runs}
    approvals = session.exec(select(RunApproval).where(RunApproval.status.in_(["pending", "queued"]))).all()
    for approval in approvals:
        run = run_lookup.get(approval.run_id)
        if not run:
            continue
        if user.role != "admin" and run.project_id and run.project_id not in {p.id for p in projects}:
            continue
        project = project_lookup.get(run.project_id)
        project_key = str(project.id) if project else "none"
        stat = project_stats.setdefault(project_key, DashboardProjectApprovalStat(
            project_id=project.id if project else None,
            project_name=project.name if project else "(no-project)",
        ))
        stat.waiting_approval_count += 1
        if approval.status == "pending":
            actionable_approval_count += 1
        else:
            queued_approval_count += 1
        overdue, due_soon, minutes = _approval_alert_state(approval)
        if overdue:
            overdue_approval_count += 1
            stat.overdue_approval_count += 1
        elif due_soon:
            due_soon_approval_count += 1
        if overdue or due_soon:
            alerts.append(ApprovalAlertItem(
                id=approval.id,
                run_id=approval.run_id,
                phase=approval.phase,
                project_name=project.name if project else None,
                run_title=run.title,
                required_role=approval.required_role,
                due_at=approval.due_at,
                severity="critical" if overdue else "warning",
                sla_minutes_remaining=minutes,
            ))
    pending_invite_count = 0
    pending_request_count = 0
    invites = session.exec(select(ProjectMembershipInvite).where(ProjectMembershipInvite.status == "pending")).all()
    requests = session.exec(select(ProjectAccessRequest).where(ProjectAccessRequest.status == "pending")).all()
    allowed_projects = {p.id for p in projects}
    for invite in invites:
        if user.role == "admin" or invite.project_id in allowed_projects:
            pending_invite_count += 1
            key = str(invite.project_id)
            stat = project_stats.setdefault(key, DashboardProjectApprovalStat(project_id=invite.project_id, project_name=project_lookup.get(invite.project_id).name if invite.project_id in project_lookup else "(unknown)"))
            stat.pending_invite_count += 1
    for request in requests:
        if user.role == "admin" or request.project_id in allowed_projects:
            pending_request_count += 1
            key = str(request.project_id)
            stat = project_stats.setdefault(key, DashboardProjectApprovalStat(project_id=request.project_id, project_name=project_lookup.get(request.project_id).name if request.project_id in project_lookup else "(unknown)"))
            stat.pending_request_count += 1

    hotspots = sorted(project_stats.values(), key=lambda item: (item.overdue_approval_count, item.waiting_approval_count, item.pending_request_count, item.pending_invite_count), reverse=True)[:8]
    return DashboardSummary(
        project_count=len(projects),
        agent_count=len(session.exec(select(AgentCatalog)).all()),
        run_count=len(runs),
        running_count=sum(1 for r in runs if r.queue_status in {"queued", "resuming", "running", "retry_scheduled", "waiting_approval"}),
        completed_count=sum(1 for r in runs if r.status == "completed"),
        blocked_count=sum(1 for r in runs if r.status in {"blocked", "failed"}),
        dead_lettered_count=sum(1 for r in runs if r.queue_status == "dead_lettered"),
        waiting_approval_count=sum(1 for r in runs if r.queue_status == "waiting_approval"),
        worker_count=worker_summary["worker_count"],
        active_worker_count=worker_summary["active_worker_count"],
        actionable_approval_count=actionable_approval_count,
        queued_approval_count=queued_approval_count,
        overdue_approval_count=overdue_approval_count,
        due_soon_approval_count=due_soon_approval_count,
        pending_invite_count=pending_invite_count,
        pending_request_count=pending_request_count,
        latest_runs=latest_runs,
        approval_alerts=ApprovalAlertSnapshot(items=alerts[:12], overdue_count=overdue_approval_count, due_soon_count=due_soon_approval_count),
        project_hotspots=hotspots,
    )


@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard(session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer"))) -> DashboardSummary:
    return _build_summary(session, user)


@router.get("/dashboard/stream")
async def stream_dashboard(session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer"))):
    async def event_generator():
        last_payload = None
        while True:
            with Session(session.bind) as stream_session:
                payload = _build_summary(stream_session, user).model_dump(mode="json")
                dumped = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                if dumped != last_payload:
                    yield f"event: snapshot\ndata: {dumped}\n\n"
                    last_payload = dumped
            await asyncio.sleep(settings.event_stream_poll_interval_seconds)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
