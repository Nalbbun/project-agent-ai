from typing import Any

from pydantic import BaseModel


class FoundationGuardItem(BaseModel):
    code: str
    title: str
    status: str
    summary: str
    evidence: dict[str, Any] = {}
    required: bool = True


class FoundationGuardSnapshot(BaseModel):
    status: str
    generated_at: str
    items: list[FoundationGuardItem]
    warnings: list[str] = []

