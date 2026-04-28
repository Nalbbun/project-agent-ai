from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class EventRead(BaseModel):
    id: UUID
    run_id: UUID
    step_id: Optional[UUID]
    level: str
    event_type: str
    message: str
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    created_at: datetime
