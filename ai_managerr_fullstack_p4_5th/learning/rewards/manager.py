from __future__ import annotations

from typing import Any, Dict

from .common import presence_score, safe_json_load, schema_pass_rate, weighted_sum


def compute_manager_reward(completion_text: str, schema_path: str) -> Dict[str, Any]:
    pred = safe_json_load(completion_text)
    plan = pred.get("output", {}).get("execution_plan", []) if pred else []
    ordered = 1.0 if plan and [s["step"] for s in plan] == sorted(s["step"] for s in plan) else 0.0
    parts = {
        "schema": schema_pass_rate(pred, schema_path),
        "plan_presence": presence_score(pred, ["output.execution_plan", "output.missing_info_questions", "output.merge_strategy"]),
        "ordering": ordered,
        "coverage": 1.0 if len(plan) >= 4 else 0.3,
    }
    weights = {"schema": 0.20, "plan_presence": 0.30, "ordering": 0.25, "coverage": 0.25}
    result = weighted_sum(parts, weights)
    return {"reward": result.total, "details": result.details}
