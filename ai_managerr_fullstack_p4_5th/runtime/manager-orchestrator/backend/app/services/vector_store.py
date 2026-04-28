from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx

from app.core.config import get_settings

settings = get_settings()


class VectorStoreService:
    def __init__(self) -> None:
        self.settings = settings
        self._client = None
        self._models = None

    @property
    def enabled(self) -> bool:
        return bool(self.settings.vector_store_enabled and self.settings.vector_store_provider == "qdrant")

    def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "status": "disabled"}
        client = self._ensure_client()
        if client is None:
            return {"enabled": True, "status": "unavailable"}
        try:
            info = client.get_collections()
            return {
                "enabled": True,
                "status": "ok",
                "collections": [collection.name for collection in info.collections],
                "embedding_provider": self.settings.vector_embedding_provider,
            }
        except Exception as exc:  # noqa: BLE001
            return {"enabled": True, "status": "error", "detail": repr(exc)}

    @property
    def knowledge_collection(self) -> str:
        return f"{self.settings.vector_collection_prefix}_knowledge"

    @property
    def artifact_collection(self) -> str:
        return f"{self.settings.vector_collection_prefix}_artifacts"

    def ensure_collections(self) -> None:
        if not self.enabled:
            return
        client = self._ensure_client()
        models = self._models
        if client is None or models is None:
            return
        existing = {collection.name for collection in client.get_collections().collections}
        for name in (self.knowledge_collection, self.artifact_collection):
            if name in existing:
                continue
            client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(size=self.settings.vector_dimension, distance=models.Distance.COSINE),
            )

    def upsert_project_knowledge(self, knowledge: Any) -> None:
        if not self.enabled:
            return
        self.ensure_collections()
        client = self._ensure_client()
        models = self._models
        if client is None or models is None:
            return
        text = "\n".join(filter(None, [knowledge.title, knowledge.summary or "", knowledge.content]))
        chunks = self._chunk_text(text)
        points = []
        for idx, chunk in enumerate(chunks):
            points.append(
                models.PointStruct(
                    id=str(uuid5(NAMESPACE_URL, f"knowledge:{knowledge.id}:{idx}")),
                    vector=self.embed_text(chunk),
                    payload={
                        "project_id": str(knowledge.project_id),
                        "source_id": str(knowledge.id),
                        "source_type": "project-knowledge",
                        "title": knowledge.title,
                        "summary": knowledge.summary,
                        "content": chunk,
                        "tags": knowledge.tags or [],
                        "chunk_index": idx,
                    },
                )
            )
        if points:
            client.upsert(collection_name=self.knowledge_collection, points=points, wait=True)

    def delete_project_knowledge(self, knowledge_id: UUID | str) -> None:
        self._delete_by_source(self.knowledge_collection, knowledge_id)

    def upsert_artifact(self, artifact: Any, project_id: UUID | str | None = None) -> None:
        if not self.enabled or artifact.artifact_type not in self.settings.vector_artifact_type_list:
            return
        self.ensure_collections()
        client = self._ensure_client()
        models = self._models
        if client is None or models is None:
            return
        base_text = "\n".join(filter(None, [artifact.name, artifact.summary or "", self._stringify(artifact.content)]))
        chunks = self._chunk_text(base_text)
        points = []
        for idx, chunk in enumerate(chunks):
            points.append(
                models.PointStruct(
                    id=str(uuid5(NAMESPACE_URL, f"artifact:{artifact.id}:{idx}")),
                    vector=self.embed_text(chunk),
                    payload={
                        "project_id": str(project_id) if project_id else None,
                        "run_id": str(artifact.run_id),
                        "step_id": str(artifact.step_id) if artifact.step_id else None,
                        "source_id": str(artifact.id),
                        "source_type": artifact.artifact_type,
                        "title": artifact.name,
                        "summary": artifact.summary,
                        "content": chunk,
                        "chunk_index": idx,
                    },
                )
            )
        if points:
            client.upsert(collection_name=self.artifact_collection, points=points, wait=True)

    def delete_artifact(self, artifact_id: UUID | str) -> None:
        self._delete_by_source(self.artifact_collection, artifact_id)

    def search(self, project_id: UUID | None, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        self.ensure_collections()
        client = self._ensure_client()
        models = self._models
        if client is None or models is None:
            return []
        query_vector = self.embed_text(query)
        results: list[dict[str, Any]] = []
        for collection, fallback_source_type in (
            (self.knowledge_collection, "project-knowledge"),
            (self.artifact_collection, "artifact"),
        ):
            query_filter = None
            if project_id:
                query_filter = models.Filter(
                    must=[models.FieldCondition(key="project_id", match=models.MatchValue(value=str(project_id)))]
                )
            try:
                hits = client.search(
                    collection_name=collection,
                    query_vector=query_vector,
                    query_filter=query_filter,
                    limit=max(top_k * 2, 8),
                    with_payload=True,
                )
            except Exception:
                continue
            for hit in hits:
                payload = dict(hit.payload or {})
                payload.setdefault("source_type", fallback_source_type)
                payload["score"] = float(getattr(hit, "score", 0.0))
                results.append(payload)
        results.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        normalized: list[dict[str, Any]] = []
        seen: set[tuple[str, int]] = set()
        for item in results:
            dedupe_key = (str(item.get("source_id")), int(item.get("chunk_index", 0)))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            normalized.append(
                {
                    "source": item.get("title") or item.get("source_id"),
                    "source_type": item.get("source_type"),
                    "score": item.get("score", 0.0),
                    "summary": item.get("summary") or self._excerpt(item.get("content") or ""),
                    "content": item.get("content") or "",
                    "source_id": item.get("source_id"),
                    "chunk_index": int(item.get("chunk_index", 0)),
                }
            )
            if len(normalized) >= top_k:
                break
        return normalized

    def embed_text(self, text: str) -> list[float]:
        if self.settings.vector_embedding_provider == "openai-compatible" and self.settings.vector_embedding_base_url:
            try:
                return self._remote_embed(text)
            except Exception:
                pass
        return self._hash_embed(text)

    def _remote_embed(self, text: str) -> list[float]:
        url = self.settings.vector_embedding_base_url.rstrip("/") + "/embeddings"
        headers = {"Content-Type": "application/json"}
        if self.settings.vector_embedding_api_key:
            headers["Authorization"] = f"Bearer {self.settings.vector_embedding_api_key}"
        response = httpx.post(
            url,
            headers=headers,
            json={"model": self.settings.vector_embedding_model, "input": text},
            timeout=self.settings.rag_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("data") or []
        if not embeddings:
            raise ValueError("No embedding returned")
        raw = embeddings[0].get("embedding") or []
        if not raw:
            raise ValueError("Empty embedding returned")
        vector = [float(x) for x in raw[: self.settings.vector_dimension]]
        if len(vector) < self.settings.vector_dimension:
            vector.extend([0.0] * (self.settings.vector_dimension - len(vector)))
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 8) for value in vector]

    def _hash_embed(self, text: str) -> list[float]:
        tokens = self._tokenize(text)
        vector = [0.0] * self.settings.vector_dimension
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            for offset in range(0, len(digest), 4):
                idx = int.from_bytes(digest[offset : offset + 2], "little") % self.settings.vector_dimension
                sign = 1.0 if digest[offset + 2] % 2 == 0 else -1.0
                weight = 1.0 + (digest[offset + 3] / 255.0)
                vector[idx] += sign * weight
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 8) for value in vector]

    def _delete_by_source(self, collection_name: str, source_id: UUID | str) -> None:
        if not self.enabled:
            return
        client = self._ensure_client()
        models = self._models
        if client is None or models is None:
            return
        try:
            client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[models.FieldCondition(key="source_id", match=models.MatchValue(value=str(source_id)))]
                    )
                ),
                wait=True,
            )
        except Exception:
            return

    def _ensure_client(self):
        if not self.enabled:
            return None
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import QdrantClient, models
        except Exception:
            return None
        self._models = models
        self._client = QdrantClient(
            url=self.settings.vector_store_url,
            api_key=self.settings.vector_store_api_key or None,
            timeout=self.settings.rag_timeout_seconds,
        )
        return self._client

    def _chunk_text(self, text: str) -> list[str]:
        clean = re.sub(r"\s+", " ", (text or "")).strip()
        if not clean:
            return []
        chunks: list[str] = []
        size = self.settings.vector_chunk_size
        overlap = min(self.settings.vector_chunk_overlap, max(size // 3, 1))
        start = 0
        while start < len(clean):
            end = min(len(clean), start + size)
            chunks.append(clean[start:end])
            if end == len(clean):
                break
            start = max(0, end - overlap)
        return chunks

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [token for token in re.findall(r"[A-Za-z0-9가-힣_-]+", (text or "").lower()) if len(token) > 1]

    @staticmethod
    def _stringify(content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        return json.dumps(content, ensure_ascii=False)

    @staticmethod
    def _excerpt(text: str, limit: int = 280) -> str:
        return (text or "").strip()[:limit]
