import uuid
from typing import Optional

from sqlalchemy import Column, Text
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.models.common import TimestampedModel


class ProjectKnowledge(TimestampedModel, table=True):
    __tablename__ = "project_knowledge"

    project_id: uuid.UUID = Field(foreign_key="project.id", index=True)
    title: str = Field(max_length=160, index=True)
    source_type: str = Field(default="note", max_length=40)
    tags: Optional[list[str]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    content: str = Field(sa_column=Column(Text, nullable=False))
    summary: Optional[str] = Field(default=None, sa_column=Column(Text))
