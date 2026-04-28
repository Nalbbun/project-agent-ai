
#!/usr/bin/env python3
import json
from pathlib import Path
from collections import defaultdict
from jsonschema import Draft202012Validator, RefResolver

BASE_DIR = Path(__file__).resolve().parents[1]
SCHEMA_DIR = BASE_DIR / "schemas"
ROLE_DIRS = ["pm","architect","dev-fe","dev-be","dev-db","qa","secops","manager"]

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def build_validator(role: str):
    schema_path = SCHEMA_DIR / f"{role}.schema.json"
    common_path = SCHEMA_DIR / "common-defs.schema.json"
    schema = load_json(schema_path)
    common = load_json(common_path)
    store = {
        schema.get("$id"): schema,
        common.get("$id"): common,
        schema_path.name: schema,
        common_path.name: common,
    }
    resolver = RefResolver.from_schema(schema, store=store)
    return Draft202012Validator(schema, resolver=resolver)

def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            yield lineno, json.loads(line)

def validate_role(role: str):
    validator = build_validator(role)
    role_path = BASE_DIR / role
    results = []
    for jsonl_path in sorted(role_path.glob("*.jsonl")):
        passed = 0
        failed = 0
        errors = []
        for lineno, row in iter_jsonl(jsonl_path):
            row_errors = sorted(validator.iter_errors(row), key=lambda e: list(e.absolute_path))
            if row_errors:
                failed += 1
                errors.append({
                    "line": lineno,
                    "id": row.get("id"),
                    "errors": [
                        {
                            "path": "/" + "/".join(str(p) for p in err.absolute_path),
                            "message": err.message
                        } for err in row_errors
                    ]
                })
            else:
                passed += 1
        results.append({
            "file": str(jsonl_path.relative_to(BASE_DIR)),
            "passed": passed,
            "failed": failed,
            "valid": failed == 0,
            "errors": errors[:20]
        })
    return results

def main():
    summary = {"all_valid": True, "roles": {}, "totals": {"files": 0, "rows_passed": 0, "rows_failed": 0}}
    for role in ROLE_DIRS:
        role_results = validate_role(role)
        role_valid = all(item["valid"] for item in role_results)
        summary["roles"][role] = {
            "all_valid": role_valid,
            "files": role_results
        }
        summary["all_valid"] = summary["all_valid"] and role_valid
        summary["totals"]["files"] += len(role_results)
        summary["totals"]["rows_passed"] += sum(item["passed"] for item in role_results)
        summary["totals"]["rows_failed"] += sum(item["failed"] for item in role_results)

    report_path = BASE_DIR / "reports" / "validation_report.json"
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append(f"all_valid={summary['all_valid']}")
    lines.append(f"files={summary['totals']['files']} passed={summary['totals']['rows_passed']} failed={summary['totals']['rows_failed']}")
    for role, info in summary["roles"].items():
        role_passed = sum(item["passed"] for item in info["files"])
        role_failed = sum(item["failed"] for item in info["files"])
        lines.append(f"{role}: valid={info['all_valid']} passed={role_passed} failed={role_failed}")
    text_path = BASE_DIR / "reports" / "validation_summary.txt"
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
