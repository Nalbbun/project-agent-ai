from __future__ import annotations

from typing import Any

REQUIRED_KEYS: dict[str, list[str]] = {
    "manager": ["execution_plan", "missing_info_questions", "merge_strategy"],
    "pm": ["summary", "functional_requirements", "non_functional_requirements", "questions", "acceptance_criteria"],
    "architect": ["architecture_style", "components", "apis", "database", "sequence", "adrs"],
    "dev-fe": ["deliverables", "files"],
    "dev-be": ["deliverables", "files"],
    "dev-db": ["ddl", "indexes", "migration"],
    "qa": ["verdict", "test_cases"],
    "secops": ["verdict", "findings", "hardening_actions"],
}


class SchemaValidator:
    def validate(self, role: str, payload: dict[str, Any]) -> tuple[bool, list[str]]:
        if not isinstance(payload, dict):
            return False, ["payload must be a JSON object"]
        missing = [key for key in REQUIRED_KEYS.get(role, []) if key not in payload]
        if missing:
            return False, [f"missing required key: {key}" for key in missing]
        return True, []
