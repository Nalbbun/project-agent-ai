#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROLES = ["pm", "architect", "dev-fe", "dev-be", "dev-db", "qa", "secops", "manager"]


def read_jsonl(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def normalize_for_runtime(sample: dict[str, Any], idx: int) -> dict[str, Any]:
    role = sample["role"]
    sample = json.loads(json.dumps(sample, ensure_ascii=False))
    sample["id"] = f"runtime-sample-{idx:04d}-{sample['id']}"
    sample.setdefault("metadata", {})
    sample["metadata"]["source"] = "runtime-export-sample"
    sample["metadata"]["version"] = "step7-2"
    sample["metadata"].setdefault("tags", [])
    sample["metadata"]["tags"] = sorted(set(sample["metadata"]["tags"] + ["runtime-export", "step7-2"]))
    output = sample.setdefault("output", {})
    if role in {"dev-fe", "dev-be"}:
        output.setdefault("deliverables", [item.get("path", "file") for item in output.get("files", [])])
    if role == "qa":
        output.setdefault("verdict", "pass")
    if role == "secops":
        output.setdefault("verdict", "pass")
    sample["metadata"]["runtime"] = {
        "run_id": f"sample-run-{idx:04d}",
        "step_id": f"sample-step-{idx:04d}",
        "project_id": "sample-project",
        "phase": "manager-merge" if role == "manager" else role,
        "agent_code": role,
        "run_status": "completed",
        "queue_status": "completed",
        "backend_name": "sample-backend",
        "target_model": f"{role}-lora",
        "schema_valid": True,
        "execution_ms": 100 + idx,
        "retry_count": 0,
        "failure_category": None,
        "rag_context": [{"title": "sample project knowledge", "summary": "runtime export sample context", "score": 0.9}],
        "tool_reports": [{"tool": "sample", "status": "pass", "detail": "synthetic runtime sample"}],
        "artifacts": [{"artifact_type": "tool-report", "name": f"{role}.tool.json", "content": {"status": "pass"}}],
        "events": [{"event_type": "step.completed", "level": "info"}],
        "approvals": [{"status": "approved", "required_role": "reviewer"}] if role == "manager" else [],
        "replay_audits": [{"mode": "from-last-failed", "result_status": "completed"}] if idx % 5 == 0 else [],
        "sandbox": {"mode": "docker", "network_enabled": False, "read_only": True},
    }
    return sample


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 20 deterministic runtime-export samples from v1 examples.")
    parser.add_argument("--data-dir", default="data_examples")
    parser.add_argument("--out-dir", default="data_runtime_exports/step7_2_sample")
    parser.add_argument("--count", type=int, default=20)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.jsonl"):
        stale.unlink()

    samples: list[dict[str, Any]] = []
    role_offsets = {role: 0 for role in ROLES}
    while len(samples) < args.count:
        for role in ROLES:
            source = data_dir / role / f"{role}.train.sample.jsonl"
            rows = list(read_jsonl(source))
            row = rows[role_offsets[role] % len(rows)]
            role_offsets[role] += 1
            samples.append(normalize_for_runtime(row, len(samples) + 1))
            if len(samples) >= args.count:
                break

    counts: dict[str, int] = {}
    handles: dict[str, Any] = {}
    try:
        for sample in samples:
            role = sample["role"]
            counts[role] = counts.get(role, 0) + 1
            if role not in handles:
                handles[role] = (out_dir / f"{role}.runtime.step7-2.sample.jsonl").open("w", encoding="utf-8")
            handles[role].write(json.dumps(sample, ensure_ascii=False) + "\n")
    finally:
        for handle in handles.values():
            handle.close()

    manifest = {"version": "step7-2", "total": len(samples), "roles": counts}
    (out_dir / "manifest.step7-2.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

