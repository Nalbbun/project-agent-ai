from __future__ import annotations

from typing import Any, Dict

from .common import presence_score, safe_json_load, schema_pass_rate, weighted_sum


def compute_qa_reward(completion_text: str, schema_path: str) -> Dict[str, Any]:
    pred = safe_json_load(completion_text)
    cases = pred.get("output", {}).get("test_cases", []) if pred else []
    parts = {
        "schema": schema_pass_rate(pred, schema_path),
        "traceability": presence_score(pred, ["output.test_cases", "output.boundary_cases", "output.regression_checklist"]),
        "gwt_format": 1.0 if cases and all(all(k in c for k in ("given", "when", "then")) for c in cases) else 0.0,
        "diversity": 1.0 if len(cases) >= 3 else 0.4,
    }
    weights = {"schema": 0.20, "traceability": 0.30, "gwt_format": 0.30, "diversity": 0.20}
    result = weighted_sum(parts, weights)
    return {"reward": result.total, "details": result.details}
