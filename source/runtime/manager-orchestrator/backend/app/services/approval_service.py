from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.approval import RunApproval
from app.models.run import OrchestrationRun, OrchestrationStep
from app.models.user_account import UserAccount

settings = get_settings()


class ApprovalService:
    def __init__(self, session: Session):
        self.session = session

    def _stage_roles_for_phase(self, phase: str) -> list[str]:
        return settings.approval_policy_map.get(phase, [settings.approval_default_role])

    def _due_at_for_phase(self, phase: str) -> datetime:
        hours = settings.approval_sla_phase_hours_map.get(phase, settings.approval_sla_hours)
        return datetime.utcnow() + timedelta(hours=hours)

    def get_or_create_pending(self, run: OrchestrationRun, step: OrchestrationStep, requested_by_user_id=None) -> RunApproval:
        approvals = self.session.exec(
            select(RunApproval)
            .where(RunApproval.run_id == run.id)
            .where(RunApproval.step_id == step.id)
            .order_by(RunApproval.stage_index.asc())
        ).all()
        stage_roles = self._stage_roles_for_phase(step.phase)
        if not approvals:
            approvals = []
            for idx, role in enumerate(stage_roles, start=1):
                approval = RunApproval(
                    run_id=run.id,
                    step_id=step.id,
                    phase=step.phase,
                    status="pending" if idx == 1 else "queued",
                    required_role=role,
                    stage_index=idx,
                    stage_total=len(stage_roles),
                    requested_by_user_id=requested_by_user_id,
                    due_at=self._due_at_for_phase(step.phase) if idx == 1 else None,
                )
                self.session.add(approval)
                approvals.append(approval)
            self.session.commit()
            for approval in approvals:
                self.session.refresh(approval)
        pending = next((approval for approval in approvals if approval.status == "pending"), None)
        if pending:
            if not pending.due_at:
                pending.due_at = self._due_at_for_phase(step.phase)
                self.session.add(pending)
                self.session.commit()
                self.session.refresh(pending)
            return pending
        approved_but_not_final = next((approval for approval in approvals if approval.status == "queued"), None)
        if approved_but_not_final:
            approved_but_not_final.status = "pending"
            approved_but_not_final.due_at = self._due_at_for_phase(step.phase)
            self.session.add(approved_but_not_final)
            self.session.commit()
            self.session.refresh(approved_but_not_final)
            return approved_but_not_final
        return approvals[-1]

    def list_for_run(self, run_id: UUID) -> list[RunApproval]:
        return self.session.exec(select(RunApproval).where(RunApproval.run_id == run_id).order_by(RunApproval.created_at.asc())).all()

    def decide(self, run_id: UUID, approval_id: UUID, user: UserAccount, decision: str, note: str | None = None) -> RunApproval:
        approval = self.session.get(RunApproval, approval_id)
        run = self.session.get(OrchestrationRun, run_id)
        if not approval or not run or approval.run_id != run.id:
            raise HTTPException(status_code=404, detail="Approval not found")
        if approval.status != "pending":
            raise HTTPException(status_code=409, detail="Approval already decided")
        if user.role != "admin" and user.role != approval.required_role:
            raise HTTPException(status_code=403, detail="Approval role mismatch")
        approval.status = decision
        approval.decided_by_user_id = user.id
        approval.decision_at = datetime.utcnow()
        approval.note = note
        self.session.add(approval)
        step = self.session.get(OrchestrationStep, approval.step_id) if approval.step_id else None
        if decision == "approved":
            next_stage = self.session.exec(
                select(RunApproval)
                .where(RunApproval.run_id == run.id)
                .where(RunApproval.step_id == approval.step_id)
                .where(RunApproval.stage_index == approval.stage_index + 1)
            ).first()
            if next_stage:
                next_stage.status = "pending"
                next_stage.due_at = self._due_at_for_phase(approval.phase)
                self.session.add(next_stage)
                if step:
                    step.status = "waiting_approval"
                    step.error_message = f"Approval stage {next_stage.stage_index}/{next_stage.stage_total} pending"
                    self.session.add(step)
                run.queue_status = "waiting_approval"
                run.status = "waiting_approval"
                run.waiting_reason = f"{approval.phase}:stage-{next_stage.stage_index}"
                run.updated_at = datetime.utcnow()
                self.session.add(run)
            else:
                if step and step.status == "waiting_approval":
                    step.status = "pending"
                    step.error_message = None
                    self.session.add(step)
                if settings.approval_auto_resume:
                    run.queue_status = "resuming"
                    run.status = "queued"
                    run.waiting_reason = None
                    run.next_attempt_at = datetime.utcnow()
                    run.updated_at = datetime.utcnow()
                    self.session.add(run)
        else:
            if step:
                step.status = "blocked"
                step.error_message = note or "Approval rejected"
                self.session.add(step)
            run.queue_status = "approval_rejected"
            run.status = "blocked"
            run.waiting_reason = f"approval_rejected:{approval.phase}:stage-{approval.stage_index}"
            run.last_error = note or "Approval rejected"
            run.updated_at = datetime.utcnow()
            self.session.add(run)
        self.session.commit()
        self.session.refresh(approval)
        return approval
