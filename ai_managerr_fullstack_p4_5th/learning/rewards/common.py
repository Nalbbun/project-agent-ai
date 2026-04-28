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
