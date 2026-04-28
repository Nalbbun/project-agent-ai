import uuid
from typing import Optional

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.models.common import TimestampedModel


class OrchestrationEvent(TimestampedModel, table=True):
    __tablename__ = "orchestration_event"

    run_id: uuid.UUID = Field(foreign_key="orchestration_run.id")
    step_id: Optional[uuid.UUID] = Field(default=None, foreign_key="orchestration_step.id")
    level: str = Field(default="info", max_length=20)
    event_type: str = Field(default="log", max_length=40)
    message: str = Field(sa_column=Column(Text, nullable=False))
    trace_id: Optional[str] = Field(default=None, max_length=120)
    request_id: Optional[str] = Field(default=None, max_length=120)
    payload: Optional[dict] = Field(default=None, sa_column=Column(JSONB, nullable=True))
