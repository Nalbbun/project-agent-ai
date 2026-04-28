from __future__ import annotations

from typing import Any, Dict

from .common import hallucination_proxy_penalty, presence_score, safe_json_load, schema_pass_rate, weighted_sum


def compute_pm_reward(completion_text: str, schema_path: str) -> Dict[str, Any]:
    pred = safe_json_load(completion_text)
    parts = {
        "schema": schema_pass_rate(pred, schema_path),
        "coverage": presence_score(pred, [
            "output.summary",
            "output.functional_requirements",
            "output.non_functional_requirements",
            "output.questions",
            "output.acceptance_criteria",
        ]),
        "clarity": 1.0 if pred and len(pred.get("output", {}).get("questions", [])) >= 2 else 0.3,
        "scope_boundary": 1.0 if pred and "out_of_scope" in pred.get("output", {}) else 0.2,
        "hallucination_penalty": 1.0 - hallucination_proxy_penalty(pred, {"id", "role", "lang", "domain", "difficulty", "input", "output", "metadata"}),
    }
    weights = {
        "schema": 0.25,
        "coverage": 0.30,
        "clarity": 0.20,
        "scope_boundary": 0.15,
        "hallucination_penalty": 0.10,
    }
    result = weighted_sum(parts, weights)
    return {"reward": result.total, "details": result.details}
