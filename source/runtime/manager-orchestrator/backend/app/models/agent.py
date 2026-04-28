from datetime import datetime
from typing import Optional

from sqlmodel import Field

from app.models.common import TimestampedModel


class AgentCatalog(TimestampedModel, table=True):
    __tablename__ = "agent_catalog"

    code: str = Field(index=True, unique=True, max_length=40)
    name: str = Field(max_length=120)
    role: str = Field(max_length=40)
    endpoint: str = Field(max_length=255)
    model: str = Field(max_length=120)
    adapter: Optional[str] = Field(default=None, max_length=120)
    prompt_key: str = Field(max_length=60)
    transport: str = Field(default="router", max_length=20)
    router_role: str = Field(max_length=40)
    request_timeout_seconds: int = Field(default=180)
    max_retries: int = Field(default=2)
    active: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
