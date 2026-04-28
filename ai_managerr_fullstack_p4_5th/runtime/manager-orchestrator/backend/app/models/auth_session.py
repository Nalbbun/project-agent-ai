from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field

from app.models.common import TimestampedModel


class AuthSession(TimestampedModel, table=True):
    __tablename__ = "auth_session"

    user_id: uuid.UUID = Field(foreign_key="user_account.id", index=True)
    token: str = Field(index=True, unique=True, max_length=255)
    expires_at: datetime
    last_seen_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
