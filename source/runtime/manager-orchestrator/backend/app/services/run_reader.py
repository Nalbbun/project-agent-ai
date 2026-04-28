from sqlmodel import Session, select

from app.models.approval import RunApproval
from app.models.artifact import Artifact
from app.models.event import OrchestrationEvent
from app.models.run import OrchestrationRun, OrchestrationStep
from app.schemas.approval import ApprovalRead
from app.schemas.common import EventRead
from app.schemas.run import ArtifactRead, RunRead, StepRead


def build_run_read(session: Session, run: OrchestrationRun) -> RunRead:
    steps = session.exec(
        select(OrchestrationStep)
        .where(OrchestrationStep.run_id == run.id)
        .order_by(OrchestrationStep.seq.asc())
    ).all()
    events = session.exec(
        select(OrchestrationEvent)
        .where(OrchestrationEvent.run_id == run.id)
        .order_by(OrchestrationEvent.created_at.asc())
    ).all()
    artifacts = session.exec(
        select(Artifact)
        .where(Artifact.run_id == run.id)
        .order_by(Artifact.created_at.asc())
    ).all()
    approvals = session.exec(
        select(RunApproval).where(RunApproval.run_id == run.id).order_by(RunApproval.created_at.asc())
    ).all()
    return RunRead(
        id=run.id,
        project_id=run.project_id,
        title=run.title,
        user_request=run.user_request,
        status=run.status,
        current_stage=run.current_stage,
        execution_mode=run.execution_mode,
        queue_status=run.queue_status,
        final_summary=run.final_summary,
        started_at=run.started_at,
        finished_at=run.finished_at,
        last_error=run.last_error,
        run_metadata=run.run_metadata,
        next_attempt_at=run.next_attempt_at,
        queue_attempt_count=run.queue_attempt_count,
        queue_owner=run.queue_owner,
        waiting_reason=run.waiting_reason,
        created_at=run.created_at,
        updated_at=run.updated_at,
        steps=[StepRead.model_validate(step, from_attributes=True) for step in steps],
        events=[EventRead.model_validate(event, from_attributes=True) for event in events],
        artifacts=[ArtifactRead.model_validate(artifact, from_attributes=True) for artifact in artifacts],
        approvals=[ApprovalRead.model_validate(approval, from_attributes=True) for approval in approvals],
    )
