from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.models.artifact import Artifact
from app.models.project_knowledge import ProjectKnowledge
from app.services.vector_store import VectorStoreService


class RagService:
    def __init__(self, session: Session):
        self.session = session
        self.vector = VectorStoreService()

    def retrieve(self, project_id: UUID | None, role: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        vector_hits = self.vector.search(project_id, f"{role}\n{query}", top_k=max(top_k, 6))
        lexical_hits = self._retrieve_lexical(project_id, role, query, top_k=max(top_k, 6))
        merged: list[dict[str, Any]] = []
        seen: set[tuple[str, str, int]] = set()
        for rank, item in enumerate(vector_hits + lexical_hits):
            key = (str(item.get("source_type")), str(item.get("source")), int(item.get("chunk_index", 0)))
            if key in seen:
                continue
            seen.add(key)
            item.setdefault("role", role)
            item.setdefault("summary", _excerpt(item.get("content") or "", set(_tokenize(query))))
            item.setdefault("score", float(max(0.0, 1.0 - (rank * 0.03))))
            merged.append(item)
            if len(merged) >= top_k:
                break
        return merged

    def _retrieve_lexical(self, project_id: UUID | None, role: str, query: str, top_k: int) -> list[dict[str, Any]]:
        role_terms = set(_tokenize(role))
        query_terms = set(_tokenize(query)) | role_terms
        candidates: list[dict[str, Any]] = []

        if project_id:
            docs = self.session.exec(
                select(ProjectKnowledge)
                .where(ProjectKnowledge.project_id == project_id)
                .order_by(ProjectKnowledge.created_at.desc())
            ).all()
            for doc in docs:
                text = "\n".join([doc.title, doc.summary or "", doc.content])
                score = _score(query_terms, text, extra_terms=doc.tags or [])
                if score > 0:
                    candidates.append(
                        {
                            "source": doc.title,
                            "source_type": "project-knowledge",
                            "role": role,
                            "score": score,
                            "summary": doc.summary or _excerpt(text, query_terms),
                            "content": _excerpt(text, query_terms, limit=1200),
                            "source_id": str(getattr(doc, "id", doc.title)),
                            "chunk_index": 0,
                        }
                    )

        artifacts = self.session.exec(
            select(Artifact)
            .where(Artifact.artifact_type.in_(["step-output", "tool-report", "project-context", "rag-context"]))
            .order_by(Artifact.created_at.desc())
        ).all()
        for artifact in artifacts:
            content_text = _stringify_content(artifact.content)
            text = "\n".join([artifact.name, artifact.summary or "", content_text])
            score = _score(query_terms, text)
            if score > 0:
                candidates.append(
                    {
                        "source": artifact.name,
                        "source_type": artifact.artifact_type,
                        "role": role,
                        "score": score,
                        "summary": artifact.summary or _excerpt(text, query_terms),
                        "content": _excerpt(text, query_terms, limit=1200),
                        "source_id": str(getattr(artifact, "id", artifact.name)),
                        "chunk_index": 0,
                    }
                )

        candidates.sort(
            key=lambda item: (item.get("score", 0), item.get("source_type") == "project-knowledge"),
            reverse=True,
        )
        return candidates[:top_k]


def _tokenize(text: str) -> list[str]:
    return [token for token in re.findall(r"[A-Za-z0-9가-힣_-]+", (text or "").lower()) if len(token) > 1]


def _score(query_terms: set[str], text: str, extra_terms: list[str] | None = None) -> int:
    hay = set(_tokenize(text))
    if extra_terms:
        hay |= {term.lower() for term in extra_terms if term}
    return len(query_terms & hay)


def _excerpt(text: str, terms: set[str], limit: int = 400) -> str:
    text = text.strip()
    if not text:
        return ""
    lowered = text.lower()
    idx = min((lowered.find(term) for term in terms if term in lowered), default=-1)
    if idx < 0:
        return text[:limit]
    start = max(0, idx - 120)
    return text[start : start + limit]


def _stringify_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)
