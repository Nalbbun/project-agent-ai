from __future__ import annotations

import json
from datetime import datetime, timedelta
from time import perf_counter
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.agent import AgentCatalog
from app.models.approval import RunApproval
from app.models.artifact import Artifact
from app.models.event import OrchestrationEvent
from app.models.run import OrchestrationRun, OrchestrationStep
from app.models.run_replay_audit import RunReplayAudit
from app.schemas.run import RunCreate
from app.services.approval_service import ApprovalService
from app.services.job_queue import JobQueueService
from app.services.llm_client import AgentLLMClient
from app.services.prompts import build_prompt
from app.services.rag_service import RagService
from app.services.schema_validator import SchemaValidator
from app.services.tool_runner import ToolRunner
from app.services.vector_store import VectorStoreService

settings = get_settings()
PIPELINE: list[dict[str, Any]] = [
    {"seq": 1, "phase": "manager-plan", "agent_code": "manager", "depends_on": []},
    {"seq": 2, "phase": "pm", "agent_code": "pm", "depends_on": ["manager-plan"]},
    {"seq": 3, "phase": "architect", "agent_code": "architect", "depends_on": ["pm"]},
    {"seq": 4, "phase": "dev-fe", "agent_code": "dev-fe", "depends_on": ["architect"]},
    {"seq": 5, "phase": "dev-be", "agent_code": "dev-be", "depends_on": ["architect"]},
    {"seq": 6, "phase": "dev-db", "agent_code": "dev-db", "depends_on": ["architect"]},
    {"seq": 7, "phase": "qa", "agent_code": "qa", "depends_on": ["dev-fe", "dev-be", "dev-db"]},
    {"seq": 8, "phase": "secops", "agent_code": "secops", "depends_on": ["dev-fe", "dev-be", "dev-db"]},
    {"seq": 9, "phase": "manager-merge", "agent_code": "manager", "depends_on": ["qa", "secops"]},
]

TRANSIENT_ERROR_HINTS = ("timeout", "timed out", "503", "502", "connection", "temporarily", "too many requests")


class OrchestratorService:
    def __init__(self, session: Session):
        self.session = session
        self.client = AgentLLMClient()
        self.validator = SchemaValidator()
        self.rag = RagService(session)
        self.tools = ToolRunner(settings.artifact_path)
        self.queue = JobQueueService(session)
        self.vector = VectorStoreService()
        self.approvals = ApprovalService(session)

    def create_run(self, payload: RunCreate, requested_by_user_id=None) -> OrchestrationRun:
        run = OrchestrationRun(
            project_id=payload.project_id,
            title=payload.title,
            user_request=payload.user_request,
            status="draft",
            current_stage="created",
            execution_mode=payload.execution_mode,
            queue_status="pending",
            run_metadata={"source": "api", "requested_by_user_id": str(requested_by_user_id) if requested_by_user_id else None},
            next_attempt_at=datetime.utcnow(),
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)

        for step_def in PIPELINE:
            step = OrchestrationStep(
                run_id=run.id,
                seq=step_def["seq"],
                phase=step_def["phase"],
                agent_code=step_def["agent_code"],
                status="pending",
                input_payload={"phase": step_def["phase"], "depends_on": step_def["depends_on"]},
                max_retry_count=settings.max_step_retry_count,
            )
            self.session.add(step)
        self._event(run.id, None, "info", "run.created", "Run created", {"title": run.title})
        self.session.commit()
        return run

    def enqueue_run(self, run_id: UUID) -> OrchestrationRun:
        run = self.queue.enqueue_run(run_id)
        self._event(run.id, None, "info", "run.enqueued", "Run enqueued", {"execution_mode": run.execution_mode})
        self.session.commit()
        return run

    def cancel_run(self, run_id: UUID) -> OrchestrationRun:
        run = self.queue.cancel_run(run_id)
        self._event(run.id, None, "warning", "run.cancelled", "Run cancelled", None)
        self.session.commit()
        return run

    def resume_run(self, run_id: UUID) -> OrchestrationRun:
        run = self.session.get(OrchestrationRun, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.status not in {"failed", "cancelled", "queued", "draft", "blocked", "waiting_approval", "retrying"}:
            raise HTTPException(status_code=409, detail="Run cannot be resumed in current state")
        run.queue_status = "resuming"
        run.status = "queued"
        run.next_attempt_at = datetime.utcnow()
        run.updated_at = datetime.utcnow()
        self.session.add(run)
        self._event(run.id, None, "info", "run.resumed", "Run resumed", None)
        self.session.commit()
        return run

    def retry_step(self, run_id: UUID, step_id: UUID, mode: str = "from-step") -> OrchestrationRun:
        run = self.session.get(OrchestrationRun, run_id)
        step = self.session.get(OrchestrationStep, step_id)
        if not run or not step or step.run_id != run.id:
            raise HTTPException(status_code=404, detail="Run or step not found")
        steps = self.session.exec(select(OrchestrationStep).where(OrchestrationStep.run_id == run.id).order_by(OrchestrationStep.seq.asc())).all()
        for item in steps:
            should_reset = item.id == step.id or (mode == "from-step" and item.seq >= step.seq)
            if should_reset:
                item.status = "pending"
                item.output_payload = None
                item.output_text = None
                item.error_message = None
                item.started_at = None
                item.finished_at = None
                item.backend_name = None
                item.target_model = None
                item.schema_valid = None
                item.execution_ms = None
                item.last_attempt_at = None
                item.failure_category = None
                self.session.add(item)
        run.status = "queued"
        run.queue_status = "queued"
        run.current_stage = step.phase
        run.last_error = None
        run.next_attempt_at = datetime.utcnow()
        self.session.add(run)
        self._event(run.id, step.id, "warning", "step.retry_requested", f"Retry requested for {step.phase}", {"mode": mode})
        self.session.commit()
        return run


    def dead_letter_replay(self, run_id: UUID, mode: str = "from-last-failed", from_phase: str | None = None, note: str | None = None, requested_by_user_id: UUID | None = None) -> OrchestrationRun:
        run = self.session.get(OrchestrationRun, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        if mode not in {"requeue", "from-last-failed", "from-phase", "full-reset"}:
            raise HTTPException(status_code=400, detail="Unsupported replay mode")
        steps = self.session.exec(select(OrchestrationStep).where(OrchestrationStep.run_id == run.id).order_by(OrchestrationStep.seq.asc())).all()
        target_seq = None
        if mode == "requeue":
            target_seq = min((step.seq for step in steps if step.status in {"pending", "waiting_approval", "running"}), default=None)
        elif mode == "from-last-failed":
            failed = next((step for step in reversed(steps) if step.status in {"failed", "blocked", "waiting_approval"} or step.failure_category), None)
            target_seq = failed.seq if failed else 1
        elif mode == "from-phase":
            matched = next((step for step in steps if step.phase == (from_phase or "")), None)
            if not matched:
                raise HTTPException(status_code=404, detail="Replay phase not found")
            target_seq = matched.seq
        elif mode == "full-reset":
            target_seq = 1

        if target_seq is None:
            target_seq = 1

        previous_status = run.status
        previous_queue_status = run.queue_status
        target_phase = next((step.phase for step in steps if step.seq == target_seq), None)

        before_steps: list[dict] = []
        after_steps: list[dict] = []
        reset_step_ids: list[str] = []
        for item in steps:
            if mode == "requeue" and item.seq < target_seq:
                continue
            if item.seq >= target_seq:
                before_steps.append({
                    "id": str(item.id),
                    "seq": item.seq,
                    "phase": item.phase,
                    "status": item.status,
                    "retry_count": item.retry_count,
                    "failure_category": item.failure_category,
                    "had_output": bool(item.output_payload),
                })
                item.status = "pending"
                item.output_payload = None
                item.output_text = None
                item.error_message = None
                item.started_at = None
                item.finished_at = None
                item.backend_name = None
                item.target_model = None
                item.schema_valid = None
                item.execution_ms = None
                item.last_attempt_at = None
                item.failure_category = None
                self.session.add(item)
                reset_step_ids.append(str(item.id))
                after_steps.append({
                    "id": str(item.id),
                    "seq": item.seq,
                    "phase": item.phase,
                    "status": item.status,
                    "retry_count": item.retry_count,
                    "failure_category": item.failure_category,
                    "had_output": bool(item.output_payload),
                })
        approvals = self.session.exec(select(RunApproval).where(RunApproval.run_id == run.id)).all()
        affected_phases = {step.phase for step in steps if step.seq >= target_seq}
        removed_approval_ids: list[str] = []
        for approval in approvals:
            if approval.phase in affected_phases and approval.status in {"pending", "queued", "approved", "rejected"}:
                removed_approval_ids.append(str(approval.id))
                self.session.delete(approval)
        run.status = "queued"
        run.queue_status = "queued"
        run.current_stage = target_phase
        run.last_error = None
        run.waiting_reason = None
        run.queue_owner = None
        run.next_attempt_at = datetime.utcnow()
        run.updated_at = datetime.utcnow()
        self.session.add(run)
        audit = RunReplayAudit(
            run_id=run.id,
            requested_by_user_id=requested_by_user_id,
            mode=mode,
            from_phase=from_phase,
            target_seq=target_seq,
            target_phase=target_phase,
            note=note,
            previous_status=previous_status,
            previous_queue_status=previous_queue_status,
            result_status=run.status,
            result_queue_status=run.queue_status,
            replay_group=f"{run.id}:{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            details={
                "affected_phases": sorted(affected_phases),
                "removed_approval_ids": removed_approval_ids,
                "reset_step_ids": reset_step_ids,
                "before_steps": before_steps,
                "after_steps": after_steps,
                "target": {"seq": target_seq, "phase": target_phase},
            },
        )
        self.session.add(audit)
        self._event(run.id, None, "warning", "run.dead_letter_replay", "Dead-letter replay requested", {"mode": mode, "from_phase": from_phase, "target_seq": target_seq, "target_phase": target_phase, "note": note, "audit_id": str(audit.id)})
        self.session.commit()
        return run

    def execute_run_inline(self, run_id: str | UUID, worker_id: str | None = None) -> OrchestrationRun:
        run = self.session.get(OrchestrationRun, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.queue_status == "cancelled":
            return run

        was_claimed_by_worker = run.queue_status == "running" and run.queue_owner == worker_id and worker_id is not None
        run.queue_status = "running"
        run.status = "running"
        run.queue_owner = worker_id
        if not was_claimed_by_worker:
            run.queue_attempt_count += 1
        run.started_at = run.started_at or datetime.utcnow()
        run.updated_at = datetime.utcnow()
        self.session.add(run)
        self.session.commit()

        steps = self.session.exec(select(OrchestrationStep).where(OrchestrationStep.run_id == run.id).order_by(OrchestrationStep.seq.asc())).all()

        for step in steps:
            if run.queue_status == "cancelled":
                break
            if step.status == "completed":
                continue
            outcome = self.execute_next_step(run, step)
            self.session.refresh(run)
            self.session.refresh(step)
            if outcome in {"waiting_approval", "retry_scheduled"}:
                return run
            if step.status in {"failed", "blocked"}:
                run.status = "failed" if step.status == "failed" else "blocked"
                run.queue_status = "failed" if step.status == "failed" else "approval_rejected"
                run.current_stage = step.phase
                run.finished_at = datetime.utcnow()
                run.last_error = step.error_message
                run.queue_owner = None
                self.session.add(run)
                self.session.commit()
                return run

        run.status = "completed"
        run.queue_status = "completed"
        run.current_stage = "done"
        run.finished_at = datetime.utcnow()
        run.queue_owner = None
        merge_step = next((s for s in steps if s.phase == "manager-merge"), None)
        if merge_step and merge_step.output_payload:
            run.final_summary = merge_step.output_payload.get("final_summary")
        run.updated_at = datetime.utcnow()
        self.session.add(run)
        self._event(run.id, None, "info", "run.completed", "Run completed", {"final_summary": run.final_summary})
        self.session.commit()
        return run

    def execute_next_step(self, run: OrchestrationRun, step: OrchestrationStep) -> str | None:
        if settings.approval_enabled and step.phase in settings.approval_required_phase_list:
            approvals = self.session.exec(select(RunApproval).where(RunApproval.step_id == step.id).order_by(RunApproval.stage_index.asc())).all()
            all_approved = approvals and all(item.status == "approved" for item in approvals)
            if not all_approved:
                approval = self.approvals.get_or_create_pending(run, step)
                step.status = "waiting_approval"
                step.error_message = f"Approval required ({approval.stage_index}/{approval.stage_total})"
                run.queue_status = "waiting_approval"
                run.status = "waiting_approval"
                run.waiting_reason = f"{step.phase}:stage-{approval.stage_index}"
                run.current_stage = step.phase
                run.updated_at = datetime.utcnow()
                self.session.add(run)
                self.session.add(step)
                self._event(run.id, step.id, "warning", "step.waiting_approval", f"Approval required for {step.phase}", {"approval_id": str(approval.id), "required_role": approval.required_role, "stage_index": approval.stage_index, "stage_total": approval.stage_total})
                self.session.commit()
                return "waiting_approval"

        agent = self.session.exec(select(AgentCatalog).where(AgentCatalog.code == step.agent_code)).first()
        if not agent:
            self.record_step_failure(run, step, f"Agent not found: {step.agent_code}")
            return None

        context = self.prepare_step_context(run.id, step.seq)
        rag_context = self.rag.retrieve(run.project_id, agent.role, run.user_request, settings.rag_top_k) if settings.rag_enabled else []
        prompt = build_prompt(agent.prompt_key, run.user_request, context, rag_context)

        step.status = "running"
        step.started_at = datetime.utcnow()
        step.last_attempt_at = datetime.utcnow()
        step.prompt_text = prompt
        step.input_payload = {"user_request": run.user_request, "context": context, "rag_context": rag_context}
        run.current_stage = step.phase
        self.session.add(run)
        self.session.add(step)
        self._event(run.id, step.id, "info", "step.started", f"Executing {step.phase}", {"agent": step.agent_code})
        self.session.commit()

        started = perf_counter()
        try:
            result = self.client.invoke(agent, prompt, run.user_request, context, str(run.id), str(step.id))
            payload = result["parsed"]
            schema_valid, errors = self.validate_step_output(agent.role, payload)
            if not schema_valid:
                raise ValueError("schema_validation: " + "; ".join(errors))
            tool_reports = self._run_step_tools(run, step.phase, payload)
            self.record_step_success(run, step, result, payload, rag_context, tool_reports, int((perf_counter() - started) * 1000))
            return None
        except Exception as exc:  # noqa: BLE001
            category = self._classify_error(exc)
            if category == "transient" and step.retry_count < step.max_retry_count:
                step.retry_count += 1
                step.status = "pending"
                step.error_message = str(exc)
                step.failure_category = category
                backoff = min(settings.retry_backoff_base_seconds * (2 ** max(step.retry_count - 1, 0)), settings.retry_backoff_max_seconds)
                run.queue_status = "retry_scheduled"
                run.status = "retrying"
                run.next_attempt_at = datetime.utcnow() + timedelta(seconds=backoff)
                run.current_stage = step.phase
                run.last_error = str(exc)
                run.waiting_reason = None
                run.updated_at = datetime.utcnow()
                self.session.add(step)
                self.session.add(run)
                self._event(run.id, step.id, "warning", "step.retry_scheduled", f"Retry scheduled for {step.phase}", {"error": str(exc), "backoff_seconds": backoff, "retry_count": step.retry_count})
                self.session.commit()
                return "retry_scheduled"
            step.retry_count += 1
            self.record_step_failure(run, step, str(exc), category=category)
            return None

    def validate_step_output(self, role: str, payload: dict[str, Any]) -> tuple[bool, list[str]]:
        if not settings.schema_validation_enabled:
            return True, []
        return self.validator.validate(role, payload)

    def prepare_step_context(self, run_id: UUID, upto_seq: int) -> dict[str, Any]:
        prior_steps = self.session.exec(
            select(OrchestrationStep)
            .where(OrchestrationStep.run_id == run_id)
            .where(OrchestrationStep.seq < upto_seq)
            .where(OrchestrationStep.status == "completed")
            .order_by(OrchestrationStep.seq.asc())
        ).all()
        context: dict[str, Any] = {}
        for item in prior_steps:
            if item.output_payload:
                context[item.phase] = item.output_payload
            tool_artifacts = self.session.exec(
                select(Artifact)
                .where(Artifact.step_id == item.id)
                .where(Artifact.artifact_type == "tool-report")
                .order_by(Artifact.created_at.desc())
            ).all()
            if tool_artifacts:
                context[f"{item.phase}__tool_reports"] = [artifact.content for artifact in tool_artifacts if artifact.content]
        return context

    def record_step_success(self, run: OrchestrationRun, step: OrchestrationStep, result: dict[str, Any], payload: dict[str, Any], rag_context: list[dict[str, Any]], tool_reports: list[dict[str, Any]], execution_ms: int) -> None:
        step.output_payload = payload
        step.output_text = self._safe_dump(payload)
        step.status = "completed"
        step.finished_at = datetime.utcnow()
        step.schema_valid = True
        step.backend_name = result.get("backend_name")
        step.target_model = result.get("target_model")
        step.execution_ms = execution_ms
        step.failure_category = None
        self.session.add(step)

        artifacts_to_index: list[Artifact] = []
        artifacts_to_index.append(self._artifact(run.id, step.id, "step-output", f"{step.phase}.json", payload, summary=f"normalized output for {step.phase}"))
        raw_artifact = self._artifact(run.id, step.id, "raw-llm-response", f"{step.phase}.raw.txt", {"raw_text": result.get("raw_text")}, storage_type="text", content_type="text/plain", summary=f"raw llm response for {step.phase}")
        if rag_context:
            artifacts_to_index.append(self._artifact(run.id, step.id, "rag-context", f"{step.phase}.rag.json", {"sources": rag_context}, summary=f"retrieved rag context for {step.phase}"))
        if tool_reports:
            artifacts_to_index.append(self._artifact(run.id, step.id, "tool-report", f"{step.phase}.tool.json", {"reports": tool_reports}, summary=f"tool reports for {step.phase}"))
        run.waiting_reason = None
        self._event(run.id, step.id, "info", "step.completed", f"Completed {step.phase}", {"agent": step.agent_code, "backend": step.backend_name, "model": step.target_model, "execution_ms": execution_ms}, request_id=result.get("request_id"))
        self.session.commit()
        if self.vector.enabled:
            for artifact in artifacts_to_index:
                self.vector.upsert_artifact(artifact, project_id=run.project_id)
        _ = raw_artifact

    def record_step_failure(self, run: OrchestrationRun, step: OrchestrationStep, error_message: str, category: str = "permanent") -> None:
        step.status = "failed"
        step.error_message = error_message
        step.finished_at = datetime.utcnow()
        step.failure_category = category
        step.schema_valid = False if "missing required key" in error_message or "payload must be" in error_message or "schema_validation" in error_message else step.schema_valid
        self.session.add(step)
        run.last_error = error_message
        run.updated_at = datetime.utcnow()
        run.queue_owner = None
        self.session.add(run)
        self._event(run.id, step.id, "error", "step.failed", f"Failed {step.phase}", {"error": error_message, "retry_count": step.retry_count, "category": category})
        self.session.commit()

    def _run_step_tools(self, run: OrchestrationRun, step_phase: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        reports: list[dict[str, Any]] = []
        if step_phase.startswith("dev"):
            if settings.build_runner_enabled:
                reports.append(self.tools.run_build(str(run.id), step_phase, payload))
            if settings.lint_runner_enabled:
                reports.append(self.tools.run_lint(str(run.id), step_phase, payload))
            if settings.type_runner_enabled:
                reports.append(self.tools.run_type(str(run.id), step_phase, payload))
        if step_phase == "qa" and settings.test_runner_enabled:
            reports.append(self.tools.run_test(str(run.id), step_phase, payload))
        if step_phase == "secops" and settings.security_runner_enabled:
            reports.append(self.tools.run_scan(str(run.id), step_phase, payload))
        return reports

    def _artifact(self, run_id: UUID, step_id: UUID | None, artifact_type: str, name: str, content: dict[str, Any], storage_type: str = "json", path: str | None = None, content_type: str | None = "application/json", summary: str | None = None) -> Artifact:
        artifact = Artifact(run_id=run_id, step_id=step_id, artifact_type=artifact_type, name=name, storage_type=storage_type, path=path, content_type=content_type, summary=summary, content=content)
        self.session.add(artifact)
        return artifact

    def _event(self, run_id: UUID, step_id: UUID | None, level: str, event_type: str, message: str, payload: dict[str, Any] | None, trace_id: str | None = None, request_id: str | None = None) -> None:
        event = OrchestrationEvent(run_id=run_id, step_id=step_id, level=level, event_type=event_type, message=message, trace_id=trace_id, request_id=request_id, payload=payload)
        self.session.add(event)

    @staticmethod
    def _safe_dump(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def _classify_error(exc: Exception) -> str:
        message = str(exc).lower()
        return "transient" if any(hint in message for hint in TRANSIENT_ERROR_HINTS) else "permanent"
