import uuid
from typing import Optional

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.models.common import TimestampedModel


class Artifact(TimestampedModel, table=True):
    __tablename__ = "artifact"

    run_id: uuid.UUID = Field(foreign_key="orchestration_run.id")
    step_id: Optional[uuid.UUID] = Field(default=None, foreign_key="orchestration_step.id")
    artifact_type: str = Field(max_length=40)
    name: str = Field(max_length=120)
    storage_type: str = Field(default="json", max_length=20)
    path: Optional[str] = Field(default=None, max_length=255)
    content_type: Optional[str] = Field(default=None, max_length=120)
    summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    content: Optional[dict] = Field(default=None, sa_column=Column(JSONB, nullable=True))
