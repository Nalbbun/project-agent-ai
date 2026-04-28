from __future__ import annotations

from typing import Any, Dict

from .common import presence_score, safe_json_load, schema_pass_rate, weighted_sum


def compute_architect_reward(completion_text: str, schema_path: str) -> Dict[str, Any]:
    pred = safe_json_load(completion_text)
    parts = {
        "schema": schema_pass_rate(pred, schema_path),
        "component_coverage": presence_score(pred, [
            "output.architecture_style",
            "output.components",
            "output.apis",
            "output.database.entities",
            "output.sequence",
            "output.adrs",
        ]),
        "api_db_consistency": 1.0 if pred and pred.get("output", {}).get("apis") and pred.get("output", {}).get("database", {}).get("entities") else 0.2,
        "design_coherence": 1.0 if pred and len(pred.get("output", {}).get("components", [])) >= 2 else 0.3,
    }
    weights = {"schema": 0.25, "component_coverage": 0.30, "api_db_consistency": 0.25, "design_coherence": 0.20}
    result = weighted_sum(parts, weights)
    return {"reward": result.total, "details": result.details}
