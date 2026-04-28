from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AgentRead(BaseModel):
    id: UUID
    code: str
    name: str
    role: str
    endpoint: str
    model: str
    adapter: Optional[str] = None
    prompt_key: str
    transport: str
    router_role: str
    request_timeout_seconds: int
    max_retries: int
    active: bool
    created_at: datetime
    updated_at: datetime
