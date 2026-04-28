from datetime import datetime
from typing import Optional

from sqlmodel import Field

from app.models.common import TimestampedModel


class Project(TimestampedModel, table=True):
    __tablename__ = "project"

    name: str = Field(index=True, max_length=120)
    description: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
