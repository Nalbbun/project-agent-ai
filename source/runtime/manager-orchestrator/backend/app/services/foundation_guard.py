from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from app.core.config import Settings, get_settings
from app.models.agent import AgentCatalog
from app.models.approval import RunApproval
from app.models.artifact import Artifact
from app.models.event import OrchestrationEvent
from app.models.project_knowledge import ProjectKnowledge
from app.models.project_membership import ProjectMembership
from app.models.run import OrchestrationRun
from app.models.run_replay_audit import RunReplayAudit
from app.schemas.foundation import FoundationGuardItem, FoundationGuardSnapshot
from app.services.orchestrator import PIPELINE

FOUNDATION_GUARD_CODES = [
    "router-role-routing",
    "queue-worker-retry-dead-letter",
    "approval-rbac-project-membership",
    "artifact-event-audit-replay",
    "rag-project-knowledge-reindex",
    "runner-sandbox-isolation",
]


def _status(condition: bool, warn: bool = False) -> str:
    if condition:
        return "pass"
    return "warn" if warn else "fail"


def _count(session: Session, model: type) -> int:
    return len(session.exec(select(model)).all())


class FoundationGuardService:
    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()

    def snapshot(self) -> FoundationGuardSnapshot:
        items = [
            self._router_item(),
            self._queue_item(),
            self._access_item(),
            self._trace_item(),
            self._rag_item(),
            self._sandbox_item(),
        ]
        warnings = [item.summary for item in items if item.status == "warn"]
        overall = "pass"
        if any(item.status == "fail" for item in items):
            overall = "fail"
        elif warnings:
            overall = "warn"
        return FoundationGuardSnapshot(
            status=overall,
            generated_at=datetime.utcnow().isoformat(),
            items=items,
            warnings=warnings,
        )

    def _router_item(self) -> FoundationGuardItem:
        agents = self.session.exec(select(AgentCatalog).where(AgentCatalog.active == True)).all()  # noqa: E712
        missing_router_roles = [agent.code for agent in agents if not agent.router_role]
        pipeline_roles = sorted({step["agent_code"] for step in PIPELINE})
        condition = self.settings.use_router and bool(self.settings.router_base_url) and not missing_router_roles
        return FoundationGuardItem(
            code="router-role-routing",
            title="Router forced path + role routing",
            status=_status(condition),
            summary="Router path is enforced for active agents." if condition else "Router path or active agent router roles need attention.",
            evidence={
                "use_router": self.settings.use_router,
                "router_base_url": self.settings.router_base_url,
                "router_model_name": self.settings.router_model_name,
                "active_agent_count": len(agents),
                "missing_router_roles": missing_router_roles,
                "pipeline_agent_codes": pipeline_roles,
            },
        )

    def _queue_item(self) -> FoundationGuardItem:
        condition = (
            self.settings.job_mode == "background"
            and self.settings.max_step_retry_count > 0
            and self.settings.retry_backoff_base_seconds > 0
            and self.settings.queue_dead_letter_attempts > 0
        )
        queued = _count(self.session, OrchestrationRun)
        return FoundationGuardItem(
            code="queue-worker-retry-dead-letter",
            title="Queue/worker + retry/backoff + dead-letter",
            status=_status(condition),
            summary="Background queue, retry/backoff, and dead-letter thresholds are configured." if condition else "Queue reliability settings are incomplete.",
            evidence={
                "job_mode": self.settings.job_mode,
                "max_step_retry_count": self.settings.max_step_retry_count,
                "retry_backoff_base_seconds": self.settings.retry_backoff_base_seconds,
                "retry_backoff_max_seconds": self.settings.retry_backoff_max_seconds,
                "queue_dead_letter_attempts": self.settings.queue_dead_letter_attempts,
                "run_count": queued,
            },
        )

    def _access_item(self) -> FoundationGuardItem:
        condition = self.settings.auth_enabled and self.settings.approval_enabled and bool(self.settings.approval_policy_map)
        return FoundationGuardItem(
            code="approval-rbac-project-membership",
            title="Approval + RBAC + project membership",
            status=_status(condition),
            summary="Auth, approval policy, and project memberships are active." if condition else "Auth, approval, or approval policy is not fully enabled.",
            evidence={
                "auth_enabled": self.settings.auth_enabled,
                "approval_enabled": self.settings.approval_enabled,
                "approval_required_phases": self.settings.approval_required_phase_list,
                "approval_policy": self.settings.approval_policy_map,
                "membership_count": _count(self.session, ProjectMembership),
                "approval_count": _count(self.session, RunApproval),
            },
        )

    def _trace_item(self) -> FoundationGuardItem:
        replay_modes = ["requeue", "from-last-failed", "from-phase", "full-reset"]
        return FoundationGuardItem(
            code="artifact-event-audit-replay",
            title="Artifact/event/audit tracking with replay",
            status="pass",
            summary="Artifact, event, and replay audit tables are available for run reconstruction.",
            evidence={
                "artifact_count": _count(self.session, Artifact),
                "event_count": _count(self.session, OrchestrationEvent),
                "replay_audit_count": _count(self.session, RunReplayAudit),
                "supported_replay_modes": replay_modes,
            },
        )

    def _rag_item(self) -> FoundationGuardItem:
        condition = self.settings.rag_enabled and self.settings.vector_store_enabled
        warn = not condition
        return FoundationGuardItem(
            code="rag-project-knowledge-reindex",
            title="RAG + project knowledge + reindex",
            status=_status(condition, warn=warn),
            summary="RAG/vector indexing is enabled." if condition else "Project knowledge and reindex APIs exist, but RAG/vector indexing is disabled in this environment.",
            evidence={
                "rag_enabled": self.settings.rag_enabled,
                "rag_provider": self.settings.rag_provider,
                "vector_store_enabled": self.settings.vector_store_enabled,
                "vector_store_provider": self.settings.vector_store_provider,
                "knowledge_count": _count(self.session, ProjectKnowledge),
                "vector_artifact_types": self.settings.vector_artifact_type_list,
            },
        )

    def _sandbox_item(self) -> FoundationGuardItem:
        condition = self.settings.runner_sandbox_mode == "docker" and not self.settings.runner_sandbox_network_enabled
        warn = not condition
        return FoundationGuardItem(
            code="runner-sandbox-isolation",
            title="Runner sandbox isolation",
            status=_status(condition, warn=warn),
            summary="Runner is configured for isolated docker execution." if condition else "Runner sandbox is present, but local mode or network access weakens isolation.",
            evidence={
                "runner_sandbox_mode": self.settings.runner_sandbox_mode,
                "docker_read_only": self.settings.runner_sandbox_docker_read_only,
                "docker_user": self.settings.runner_sandbox_docker_user,
                "docker_memory": self.settings.runner_sandbox_docker_memory,
                "docker_cpus": self.settings.runner_sandbox_docker_cpus,
                "network_enabled": self.settings.runner_sandbox_network_enabled,
                "image_map": self.settings.runner_sandbox_docker_image_map,
            },
        )
