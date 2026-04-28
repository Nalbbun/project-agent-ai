import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.models.common import TimestampedModel


class OrchestrationRun(TimestampedModel, table=True):
    __tablename__ = "orchestration_run"

    project_id: Optional[uuid.UUID] = Field(default=None, foreign_key="project.id")
    title: str = Field(max_length=160)
    user_request: str = Field(sa_column=Column(Text, nullable=False))
    status: str = Field(default="draft", max_length=30)
    current_stage: Optional[str] = Field(default=None, max_length=60)
    execution_mode: str = Field(default="background", max_length=20)
    queue_status: str = Field(default="pending", max_length=30)
    final_summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    last_error: Optional[str] = Field(default=None, sa_column=Column(Text))
    run_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    next_attempt_at: Optional[datetime] = None
    queue_attempt_count: int = Field(default=0)
    queue_owner: Optional[str] = Field(default=None, max_length=120)
    waiting_reason: Optional[str] = Field(default=None, max_length=120)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class OrchestrationStep(TimestampedModel, table=True):
    __tablename__ = "orchestration_step"

    run_id: uuid.UUID = Field(foreign_key="orchestration_run.id")
    seq: int = Field(index=True)
    phase: str = Field(max_length=60)
    agent_code: str = Field(max_length=40)
    status: str = Field(default="pending", max_length=30)
    prompt_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    output_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    input_payload: Optional[dict] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    output_payload: Optional[dict] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    retry_count: int = Field(default=0)
    max_retry_count: int = Field(default=2)
    backend_name: Optional[str] = Field(default=None, max_length=80)
    target_model: Optional[str] = Field(default=None, max_length=120)
    schema_valid: Optional[bool] = None
    execution_ms: Optional[int] = None
    last_attempt_at: Optional[datetime] = None
    failure_category: Optional[str] = Field(default=None, max_length=40)
