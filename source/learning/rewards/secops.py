from __future__ import annotations

from typing import Any, Dict

from .common import presence_score, safe_json_load, schema_pass_rate, weighted_sum


def compute_secops_reward(completion_text: str, schema_path: str) -> Dict[str, Any]:
    pred = safe_json_load(completion_text)
    findings = pred.get("output", {}).get("findings", []) if pred else []
    has_severity = 1.0 if findings and all("severity" in f for f in findings) else 0.0
    parts = {
        "schema": schema_pass_rate(pred, schema_path),
        "finding_coverage": presence_score(pred, ["output.findings", "output.hardening_actions", "output.priority_order"]),
        "prioritization": has_severity,
        "actionability": 1.0 if findings and all(f.get("recommendation") for f in findings) else 0.2,
    }
    weights = {"schema": 0.20, "finding_coverage": 0.35, "prioritization": 0.20, "actionability": 0.25}
    result = weighted_sum(parts, weights)
    return {"reward": result.total, "details": result.details}
