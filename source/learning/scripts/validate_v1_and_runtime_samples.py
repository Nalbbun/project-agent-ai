#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver


ROLES = ["pm", "architect", "dev-fe", "dev-be", "dev-db", "qa", "secops", "manager"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_validator(schema: dict[str, Any], common_runtime: dict[str, Any] | None = None) -> Draft202012Validator:
    store = {}
    if common_runtime:
        store["common-runtime.schema.json"] = common_runtime
        store[common_runtime.get("$id", "common-runtime.schema.json")] = common_runtime
    return Draft202012Validator(schema, resolver=RefResolver.from_schema(schema, store=store))


def validate_jsonl(path: Path, validator: Draft202012Validator) -> dict[str, Any]:
    passed = 0
    failed = 0
    errors = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        row_errors = sorted(validator.iter_errors(row), key=lambda e: list(e.absolute_path))
        if row_errors:
            failed += 1
            errors.append({
                "line": lineno,
                "id": row.get("id"),
                "errors": [{"path": "/" + "/".join(str(p) for p in err.absolute_path), "message": err.message} for err in row_errors[:5]],
            })
        else:
            passed += 1
    return {"file": str(path), "passed": passed, "failed": failed, "valid": failed == 0, "errors": errors[:20]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate v1 examples and runtime export samples together.")
    parser.add_argument("--data-dir", default="data_examples")
    parser.add_argument("--runtime-dir", default="data_runtime_exports/step7_2_sample")
    parser.add_argument("--schemas-v1", default="schemas")
    parser.add_argument("--schemas-v2", default="schemas_v2")
    parser.add_argument("--report", default="reports/v1_runtime_validation.step7-2.json")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    runtime_dir = Path(args.runtime_dir)
    schemas_v1 = Path(args.schemas_v1)
    schemas_v2 = Path(args.schemas_v2)
    results = {"all_valid": True, "v1": [], "runtime": [], "totals": {"passed": 0, "failed": 0, "files": 0}}

    for role in ROLES:
        schema = load_json(schemas_v1 / f"{role}.schema.json")
        for path in sorted((data_dir / role).glob("*.jsonl")):
            item = validate_jsonl(path, build_validator(schema))
            results["v1"].append(item)
    common_runtime = load_json(schemas_v2 / "common-runtime.schema.json")
    for path in sorted(runtime_dir.glob("*.jsonl")):
        role = path.name.split(".runtime.", 1)[0]
        schema = load_json(schemas_v2 / f"{role}.schema.json")
        item = validate_jsonl(path, build_validator(schema, common_runtime))
        results["runtime"].append(item)

    for section in ("v1", "runtime"):
        for item in results[section]:
            results["all_valid"] = results["all_valid"] and item["valid"]
            results["totals"]["passed"] += item["passed"]
            results["totals"]["failed"] += item["failed"]
            results["totals"]["files"] += 1

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"all_valid": results["all_valid"], **results["totals"]}, ensure_ascii=False))
    return 0 if results["all_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
