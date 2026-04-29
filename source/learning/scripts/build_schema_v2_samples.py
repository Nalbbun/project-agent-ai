#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


RUNTIME_SCHEMA = {
    "$id": "common-runtime.schema.json",
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Runtime Evidence Metadata",
    "type": "object",
    "properties": {
        "run_id": {"type": ["string", "null"]},
        "step_id": {"type": ["string", "null"]},
        "project_id": {"type": ["string", "null"]},
        "phase": {"type": ["string", "null"]},
        "agent_code": {"type": ["string", "null"]},
        "run_status": {"type": ["string", "null"]},
        "queue_status": {"type": ["string", "null"]},
        "backend_name": {"type": ["string", "null"]},
        "target_model": {"type": ["string", "null"]},
        "schema_valid": {"type": ["boolean", "null"]},
        "execution_ms": {"type": ["integer", "null"], "minimum": 0},
        "retry_count": {"type": ["integer", "null"], "minimum": 0},
        "failure_category": {"type": ["string", "null"]},
        "rag_context": {"type": "array", "items": {"type": "object"}, "default": []},
        "artifacts": {"type": "array", "items": {"type": "object"}, "default": []},
        "events": {"type": "array", "items": {"type": "object"}, "default": []},
        "approvals": {"type": "array", "items": {"type": "object"}, "default": []},
        "replay_audits": {"type": "array", "items": {"type": "object"}, "default": []},
        "tool_reports": {"type": "array", "items": {"type": "object"}, "default": []},
        "sandbox": {"type": "object", "additionalProperties": True},
    },
    "additionalProperties": True,
}

RUNTIME_REQUIRED = {
    "manager": ["execution_plan", "missing_info_questions", "merge_strategy"],
    "pm": ["summary", "functional_requirements", "non_functional_requirements", "questions", "acceptance_criteria"],
    "architect": ["architecture_style", "components", "apis", "database", "sequence", "adrs"],
    "dev-fe": ["deliverables", "files"],
    "dev-be": ["deliverables", "files"],
    "dev-db": ["ddl", "indexes", "migration"],
    "qa": ["verdict", "test_cases"],
    "secops": ["verdict", "findings", "hardening_actions"],
}


def patch_schema(schema: dict) -> dict:
    patched = copy.deepcopy(schema)
    patched["$id"] = patched.get("$id", patched.get("title", "schema")).replace(".schema.json", ".v2.schema.json")
    patched["title"] = f"{patched.get('title', 'Agent Training Sample')} v2"
    metadata_defs = patched.get("$defs", {}).get("metadata", {})
    patched.setdefault("properties", {})["metadata"] = {
        "type": "object",
        "properties": {
            **metadata_defs.get("properties", {}),
            "runtime": {"$ref": "common-runtime.schema.json"},
        },
        "required": metadata_defs.get("required", ["source", "version"]),
        "additionalProperties": True,
    }
    role = patched.get("properties", {}).get("role", {}).get("const")
    output = patched.setdefault("properties", {}).setdefault("output", {"type": "object"})
    output.setdefault("type", "object")
    output.setdefault("properties", {})
    output.setdefault("required", [])
    for key in RUNTIME_REQUIRED.get(role, []):
        output["properties"].setdefault(key, {"type": ["array", "object", "string", "boolean", "null"]})
        if key not in output["required"]:
            output["required"].append(key)
    return patched


def main() -> int:
    parser = argparse.ArgumentParser(description="Build v2 schemas with optional metadata.runtime evidence.")
    parser.add_argument("--schemas", default="schemas")
    parser.add_argument("--out", default="schemas_v2")
    args = parser.parse_args()
    schema_dir = Path(args.schemas)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "common-runtime.schema.json").write_text(json.dumps(RUNTIME_SCHEMA, ensure_ascii=False, indent=2), encoding="utf-8")
    count = 0
    for schema_path in sorted(schema_dir.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        patched = patch_schema(schema)
        (out_dir / schema_path.name).write_text(json.dumps(patched, ensure_ascii=False, indent=2), encoding="utf-8")
        count += 1
    print(json.dumps({"schemas_written": count, "out": str(out_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
