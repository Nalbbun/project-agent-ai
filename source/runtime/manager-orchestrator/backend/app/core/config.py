from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "manager-orchestrator"
    app_env: str = "local"
    simulation_mode: bool = True
    database_url: str = "postgresql+psycopg://agent:agent@postgres:5432/agent_orchestrator"
    cors_origins: str = "http://localhost:5174"
    agent_config_path: str = "/app/config/agents.yaml"
    default_timeout_seconds: int = 120

    use_router: bool = True
    router_base_url: str = "http://router:8080/v1"
    router_bearer_token: str = ""
    router_model_name: str = "router-auto"
    router_request_role_field: str = "extra_body.agent_role"

    job_mode: str = "background"  # inline | background
    worker_poll_interval_seconds: int = 2
    max_step_retry_count: int = 2
    retry_backoff_base_seconds: int = 10
    retry_backoff_max_seconds: int = 120
    run_stale_after_seconds: int = 900
    step_timeout_seconds: int = 300
    worker_heartbeat_interval_seconds: int = 5
    worker_stale_after_seconds: int = 30
    worker_id: str = ""
    queue_dead_letter_attempts: int = 6

    artifact_dir: str = "/app/artifacts"

    rag_enabled: bool = False
    rag_provider: str = "qdrant"
    rag_top_k: int = 5
    rag_timeout_seconds: int = 15

    vector_store_enabled: bool = False
    vector_store_provider: str = "qdrant"
    vector_store_url: str = "http://qdrant:6333"
    vector_store_api_key: str = ""
    vector_collection_prefix: str = "agent_orchestrator"
    vector_dimension: int = 256
    vector_chunk_size: int = 700
    vector_chunk_overlap: int = 120
    vector_index_artifacts: bool = True
    vector_artifact_types: str = "project-knowledge,step-output,tool-report,rag-context"
    vector_embedding_provider: str = "hash"  # hash | openai-compatible
    vector_embedding_base_url: str = ""
    vector_embedding_api_key: str = ""
    vector_embedding_model: str = "text-embedding-3-small"

    build_runner_enabled: bool = False
    test_runner_enabled: bool = False
    lint_runner_enabled: bool = False
    type_runner_enabled: bool = False
    security_runner_enabled: bool = False
    tool_command_timeout_seconds: int = 120

    runner_sandbox_mode: str = "local"  # local | docker
    runner_sandbox_docker_image: str = "manager-orchestrator-runner-python:latest"
    runner_sandbox_docker_images: str = "python=manager-orchestrator-runner-python:latest,node=manager-orchestrator-runner-node:latest,java-maven=manager-orchestrator-runner-java:latest,java-gradle=manager-orchestrator-runner-java:latest"
    runner_sandbox_docker_user: str = "65532:65532"
    runner_sandbox_docker_read_only: bool = True
    runner_sandbox_docker_memory: str = "1024m"
    runner_sandbox_docker_cpus: str = "1.0"
    runner_sandbox_docker_pids_limit: int = 256
    runner_sandbox_network_enabled: bool = False

    schema_validation_enabled: bool = True

    auth_enabled: bool = True
    auth_session_hours: int = 12
    auth_seed_users_enabled: bool = True
    auth_admin_password: str = "admin1234!"
    auth_operator_password: str = "operator1234!"
    auth_reviewer_password: str = "reviewer1234!"
    auth_viewer_password: str = "viewer1234!"

    approval_enabled: bool = True
    approval_required_phases: str = "manager-merge"
    approval_default_role: str = "reviewer"
    approval_auto_resume: bool = True
    approval_policy: str = "manager-merge=reviewer>admin"
    approval_sla_hours: int = 24
    approval_alert_before_minutes: int = 60
    approval_sla_phase_hours: str = ""

    event_stream_poll_interval_seconds: int = 2

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value:
            raise ValueError("DATABASE_URL is required")
        if value.startswith("sqlite"):
            raise ValueError("SQLite is not supported in this runtime. Use PostgreSQL.")
        return value

    @field_validator("job_mode")
    @classmethod
    def validate_job_mode(cls, value: str) -> str:
        if value not in {"inline", "background"}:
            raise ValueError("JOB_MODE must be one of: inline, background")
        return value

    @field_validator("vector_dimension")
    @classmethod
    def validate_vector_dimension(cls, value: int) -> int:
        if value < 32:
            raise ValueError("VECTOR_DIMENSION must be >= 32")
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() not in {"local", "dev", "development", "test"}

    @property
    def artifact_path(self) -> Path:
        return Path(self.artifact_dir)

    @property
    def vector_artifact_type_list(self) -> list[str]:
        return [item.strip() for item in self.vector_artifact_types.split(",") if item.strip()]

    @property
    def approval_required_phase_list(self) -> list[str]:
        return [item.strip() for item in self.approval_required_phases.split(",") if item.strip()]

    @property
    def approval_policy_map(self) -> dict[str, list[str]]:
        policies: dict[str, list[str]] = {}
        for raw in [item.strip() for item in self.approval_policy.split(",") if item.strip()]:
            if "=" in raw:
                phase, chain = raw.split("=", 1)
                roles = [role.strip() for role in chain.split(">") if role.strip()]
                if phase.strip() and roles:
                    policies[phase.strip()] = roles
        for phase in self.approval_required_phase_list:
            policies.setdefault(phase, [self.approval_default_role])
        return policies

    @property
    def approval_sla_phase_hours_map(self) -> dict[str, int]:
        mapping: dict[str, int] = {}
        for raw in [item.strip() for item in self.approval_sla_phase_hours.split(",") if item.strip()]:
            if "=" in raw:
                phase, hours = raw.split("=", 1)
                try:
                    mapping[phase.strip()] = int(hours.strip())
                except ValueError:
                    continue
        return mapping

    @property
    def runner_sandbox_docker_image_map(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for raw in [item.strip() for item in self.runner_sandbox_docker_images.split(",") if item.strip()]:
            if "=" in raw:
                key, value = raw.split("=", 1)
                if key.strip() and value.strip():
                    mapping[key.strip()] = value.strip()
        if self.runner_sandbox_docker_image:
            mapping.setdefault("default", self.runner_sandbox_docker_image)
        return mapping


@lru_cache
def get_settings() -> Settings:
    return Settings()
