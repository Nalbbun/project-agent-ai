#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any

from jsonschema import Draft202012Validator, RefResolver

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rewards.common import runtime_reward_v2


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_jsonl(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def build_validator(schema: dict[str, Any], common_runtime: dict[str, Any]) -> Draft202012Validator:
    store = {
        "common-runtime.schema.json": common_runtime,
        common_runtime.get("$id", "common-runtime.schema.json"): common_runtime,
    }
    return Draft202012Validator(schema, resolver=RefResolver.from_schema(schema, store=store))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate per-role eval report for runtime export samples.")
    parser.add_argument("--runtime-dir", default="data_runtime_exports/step7_2_sample")
    parser.add_argument("--schemas-v2", default="schemas_v2")
    parser.add_argument("--report", default="reports/role_eval.step7-2.json")
    args = parser.parse_args()

    runtime_dir = Path(args.runtime_dir)
    schemas_v2 = Path(args.schemas_v2)
    common_runtime = load_json(schemas_v2 / "common-runtime.schema.json")
    report: dict[str, Any] = {"version": "step7-2", "roles": {}, "total_samples": 0}

    for path in sorted(runtime_dir.glob("*.jsonl")):
        role = path.name.split(".runtime.", 1)[0]
        schema = load_json(schemas_v2 / f"{role}.schema.json")
        validator = build_validator(schema, common_runtime)
        rewards = []
        schema_passed = 0
        total = 0
        detail_accumulator: dict[str, list[float]] = {}
        for row in iter_jsonl(path):
            total += 1
            if not list(validator.iter_errors(row)):
                schema_passed += 1
            reward = runtime_reward_v2(row)
            rewards.append(reward.total)
            for key, value in reward.details.items():
                detail_accumulator.setdefault(key, []).append(value)
        report["roles"][role] = {
            "samples": total,
            "schema_pass_rate": schema_passed / total if total else 0.0,
            "runtime_reward_avg": round(mean(rewards), 6) if rewards else 0.0,
            "reward_detail_avg": {key: round(mean(values), 6) for key, values in sorted(detail_accumulator.items())},
        }
        report["total_samples"] += total

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"total_samples": report["total_samples"], "roles": sorted(report["roles"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
