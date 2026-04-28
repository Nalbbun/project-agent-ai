from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.models.agent import AgentCatalog
from app.services.simulator import simulate

settings = get_settings()
JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


class AgentLLMClient:
    def invoke(self, agent: AgentCatalog, prompt: str, user_request: str, context: dict[str, Any], run_id: str | None = None, step_id: str | None = None) -> dict[str, Any]:
        if settings.simulation_mode:
            parsed = simulate(agent.role, user_request, context)
            return {
                "parsed": parsed,
                "raw_text": json.dumps(parsed, ensure_ascii=False),
                "backend_name": "simulation",
                "target_model": agent.adapter or agent.model,
                "latency_ms": 0,
                "request_id": None,
            }

        headers = {"Content-Type": "application/json"}
        if settings.router_bearer_token:
            headers["Authorization"] = f"Bearer {settings.router_bearer_token}"
        headers["x-agent-role"] = agent.router_role

        payload = {
            "model": settings.router_model_name if settings.use_router else agent.model,
            "messages": [
                {"role": "system", "content": "Always respond in JSON matching the requested schema."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "extra_body": {"agent_role": agent.router_role},
            "metadata": {
                "agent_role": agent.router_role,
                "run_id": run_id,
                "step_id": step_id,
                "adapter": agent.adapter,
            },
        }
        endpoint = settings.router_base_url if settings.use_router else agent.endpoint
        started = time.perf_counter()
        with httpx.Client(timeout=agent.request_timeout_seconds or settings.default_timeout_seconds) as client:
            response = client.post(f"{endpoint}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            latency_ms = int((time.perf_counter() - started) * 1000)
            content = self._extract_message_content(data)
            parsed = self._parse_json_like(content)
            return {
                "parsed": parsed,
                "raw_text": content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
                "backend_name": response.headers.get("x-router-backend") or endpoint,
                "target_model": response.headers.get("x-router-model") or agent.model,
                "latency_ms": latency_ms,
                "request_id": response.headers.get("x-request-id"),
            }

    @staticmethod
    def _extract_message_content(data: dict[str, Any]) -> Any:
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("LLM response does not contain choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if content is None:
            raise ValueError("LLM response content is empty")
        return content

    @classmethod
    def _parse_json_like(cls, content: Any) -> dict[str, Any]:
        if isinstance(content, dict):
            return content
        if not isinstance(content, str):
            raise ValueError("LLM content must be string or dict")

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        block = JSON_BLOCK_RE.search(content)
        if block:
            return json.loads(block.group(1))

        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = content[start:end + 1]
            return json.loads(candidate)

        raise ValueError("Failed to parse JSON content from LLM response")
