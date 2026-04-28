from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserRead(BaseModel):
    id: UUID
    username: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserRead
