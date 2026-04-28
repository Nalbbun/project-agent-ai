from __future__ import annotations

from datetime import datetime

from sqlmodel import Field

from app.models.common import TimestampedModel


class UserAccount(TimestampedModel, table=True):
    __tablename__ = "user_account"

    username: str = Field(index=True, unique=True, max_length=60)
    display_name: str = Field(max_length=120)
    password_hash: str = Field(max_length=255)
    role: str = Field(default="viewer", max_length=30)
    is_active: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
