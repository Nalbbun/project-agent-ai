from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable

import jsonschema


@dataclass
class RewardBreakdown:
    total: float
    details: Dict[str, float]


def safe_json_load(text: str) -> Dict[str, Any] | None:
    try:
        return json.loads(text)
    except Exception:
        return None


def schema_pass_rate(obj: Dict[str, Any] | None, schema_path: str) -> float:
    if obj is None:
        return 0.0
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    try:
        jsonschema.validate(obj, schema)
        return 1.0
    except Exception:
        return 0.0


def presence_score(obj: Dict[str, Any] | None, required_paths: Iterable[str]) -> float:
    if obj is None:
        return 0.0
    hits = 0
    total = 0
    for path in required_paths:
        total += 1
        cur: Any = obj
        ok = True
        for part in path.split('.'):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur not in (None, "", [], {}):
            hits += 1
    return hits / total if total else 0.0


def redundancy_penalty(text: str) -> float:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return 0.0
    unique = len(set(lines))
    return max(0.0, 1.0 - (unique / len(lines)))


def hallucination_proxy_penalty(pred: Dict[str, Any] | None, allowed_keys: set[str]) -> float:
    if pred is None:
        return 1.0
    extra = set(pred.keys()) - allowed_keys
    return min(1.0, len(extra) * 0.1)


def weighted_sum(parts: Dict[str, float], weights: Dict[str, float]) -> RewardBreakdown:
    total = 0.0
    details: Dict[str, float] = {}
    for name, value in parts.items():
        weight = weights.get(name, 0.0)
        weighted = value * weight
        total += weighted
        details[name] = weighted
    return RewardBreakdown(total=round(total, 6), details=details)


def _runtime_meta(obj: Dict[str, Any] | None) -> Dict[str, Any]:
    if not obj:
        return {}
    metadata = obj.get("metadata") or {}
    runtime = metadata.get("runtime") or {}
    return runtime if isinstance(runtime, dict) else {}


def runtime_trace_score(obj: Dict[str, Any] | None) -> float:
    runtime = _runtime_meta(obj)
    if not runtime:
        return 0.0
    required = ["run_id", "step_id", "phase", "agent_code"]
    hits = sum(1 for key in required if runtime.get(key))
    metadata_hits = sum(1 for key in ["backend_name", "target_model", "schema_valid", "execution_ms"] if runtime.get(key) not in (None, "", [], {}))
    return min(1.0, (hits / len(required) * 0.7) + (metadata_hits / 4 * 0.3))


def tool_report_score(obj: Dict[str, Any] | None) -> float:
    runtime = _runtime_meta(obj)
    reports = runtime.get("tool_reports") or []
    if not reports:
        artifacts = runtime.get("artifacts") or []
        reports = [
            artifact.get("content", {})
            for artifact in artifacts
            if isinstance(artifact, dict) and artifact.get("artifact_type") == "tool-report"
        ]
    if not reports:
        return 0.0
    values = []
    for report in reports:
        if not isinstance(report, dict):
            continue
        status = report.get("status") or report.get("content", {}).get("status")
        values.append({"pass": 1.0, "warn": 0.65, "skipped": 0.35, "fail": 0.0}.get(str(status), 0.25))
    return sum(values) / len(values) if values else 0.0


def rag_grounding_score(obj: Dict[str, Any] | None) -> float:
    runtime = _runtime_meta(obj)
    rag_context = runtime.get("rag_context") or []
    if not rag_context:
        input_payload = (obj or {}).get("input") or {}
        rag_context = input_payload.get("rag_context") or input_payload.get("current_state", {}).get("rag_context") or []
    if not rag_context:
        return 0.0
    useful = 0
    for item in rag_context:
        if isinstance(item, dict) and any(item.get(key) for key in ("title", "content", "summary", "source", "score")):
            useful += 1
    return min(1.0, useful / max(len(rag_context), 1))


def approval_readiness_score(obj: Dict[str, Any] | None) -> float:
    runtime = _runtime_meta(obj)
    approvals = runtime.get("approvals") or []
    if not approvals:
        return 0.5
    terminal = {"approved", "rejected"}
    decided = sum(1 for item in approvals if isinstance(item, dict) and item.get("status") in terminal)
    pending = sum(1 for item in approvals if isinstance(item, dict) and item.get("status") in {"pending", "queued"})
    if decided:
        return min(1.0, decided / len(approvals))
    return 0.35 if pending else 0.5


def replay_recovery_score(obj: Dict[str, Any] | None) -> float:
    runtime = _runtime_meta(obj)
    audits = runtime.get("replay_audits") or []
    if not audits:
        return 0.5
    recovered = 0
    for audit in audits:
        if not isinstance(audit, dict):
            continue
        result = audit.get("result_queue_status") or audit.get("result_status")
        if result in {"queued", "running", "completed"}:
            recovered += 1
    return recovered / len(audits)


def sandbox_safety_score(obj: Dict[str, Any] | None) -> float:
    runtime = _runtime_meta(obj)
    sandbox = runtime.get("sandbox") or {}
    if sandbox:
        mode = sandbox.get("mode") or sandbox.get("runner_sandbox_mode")
        network = sandbox.get("network_enabled")
        readonly = sandbox.get("read_only")
        score = 0.4
        if mode == "docker":
            score += 0.3
        if network is False:
            score += 0.15
        if readonly is True:
            score += 0.15
        return min(1.0, score)
    tool_score = tool_report_score(obj)
    return 0.6 if tool_score > 0 else 0.3


def runtime_reward_v2(obj: Dict[str, Any] | None) -> RewardBreakdown:
    parts = {
        "runtime_trace": runtime_trace_score(obj),
        "tool_report": tool_report_score(obj),
        "rag_grounding": rag_grounding_score(obj),
        "approval_readiness": approval_readiness_score(obj),
        "replay_recovery": replay_recovery_score(obj),
        "sandbox_safety": sandbox_safety_score(obj),
    }
    weights = {
        "runtime_trace": 0.20,
        "tool_report": 0.20,
        "rag_grounding": 0.15,
        "approval_readiness": 0.15,
        "replay_recovery": 0.15,
        "sandbox_safety": 0.15,
    }
    return weighted_sum(parts, weights)
