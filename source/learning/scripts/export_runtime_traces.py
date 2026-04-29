#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


ROLE_ALIASES = {
    "manager-plan": "manager",
    "manager-merge": "manager",
}


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return "postgresql://" + url.split("://", 1)[1]
    return url


def json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def fetch_grouped(conn, table: str, key: str, ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    if not ids:
        return {}
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"select * from {table} where {key} = any(%s)", (ids,))
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in cur.fetchall():
            grouped[str(row[key])].append(dict(row))
    return grouped


def main() -> int:
    parser = argparse.ArgumentParser(description="Export runtime run/step traces into role JSONL candidates.")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--out-dir", default="data_runtime_exports")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--status", default="completed")
    parser.add_argument("--include-invalid-schema", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    database_url = normalize_database_url(args.database_url)

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select s.*, r.title, r.user_request, r.project_id, r.status as run_status,
                       r.queue_status, r.run_metadata, r.final_summary
                from orchestration_step s
                join orchestration_run r on r.id = s.run_id
                where (%s = '' or r.status = %s)
                  and s.output_payload is not null
                  and (%s or coalesce(s.schema_valid, true) = true)
                order by r.created_at desc, s.seq asc
                limit %s
                """,
                (args.status, args.status, args.include_invalid_schema, args.limit),
            )
            steps = [dict(row) for row in cur.fetchall()]

        run_ids = sorted({str(step["run_id"]) for step in steps})
        step_ids = sorted({str(step["id"]) for step in steps})
        artifacts_by_step = fetch_grouped(conn, "artifact", "step_id", step_ids)
        events_by_step = fetch_grouped(conn, "orchestration_event", "step_id", step_ids)
        approvals_by_step = fetch_grouped(conn, "run_approval", "step_id", step_ids)
        replays_by_run = fetch_grouped(conn, "run_replay_audit", "run_id", run_ids)

    counts: dict[str, int] = defaultdict(int)
    handles: dict[str, Any] = {}
    try:
        for step in steps:
            role = ROLE_ALIASES.get(step["phase"], step["agent_code"])
            output = step["output_payload"]
            if not isinstance(output, dict):
                continue
            sample = {
                "id": f"runtime-{step['run_id']}-{step['id']}",
                "role": role,
                "lang": "mixed",
                "domain": "runtime-export",
                "difficulty": "medium",
                "input": {
                    "user_request": step["user_request"],
                    "current_state": step.get("input_payload") or {},
                    "phase": step["phase"],
                },
                "output": output,
                "metadata": {
                    "source": "runtime-export",
                    "version": "step7",
                    "tags": ["runtime", "step7", step["phase"]],
                    "runtime": {
                        "run_id": str(step["run_id"]),
                        "step_id": str(step["id"]),
                        "project_id": str(step["project_id"]) if step.get("project_id") else None,
                        "phase": step["phase"],
                        "agent_code": step["agent_code"],
                        "run_status": step.get("run_status"),
                        "queue_status": step.get("queue_status"),
                        "backend_name": step.get("backend_name"),
                        "target_model": step.get("target_model"),
                        "schema_valid": step.get("schema_valid"),
                        "execution_ms": step.get("execution_ms"),
                        "retry_count": step.get("retry_count"),
                        "failure_category": step.get("failure_category"),
                        "artifacts": artifacts_by_step.get(str(step["id"]), []),
                        "events": events_by_step.get(str(step["id"]), []),
                        "approvals": approvals_by_step.get(str(step["id"]), []),
                        "replay_audits": replays_by_run.get(str(step["run_id"]), []),
                    },
                },
            }
            if role not in handles:
                handles[role] = (out_dir / f"{role}.runtime.step7.jsonl").open("w", encoding="utf-8")
            handles[role].write(json.dumps(sample, ensure_ascii=False, default=json_default) + "\n")
            counts[role] += 1
    finally:
        for handle in handles.values():
            handle.close()

    manifest = {"version": "step7", "out_dir": str(out_dir), "total": sum(counts.values()), "roles": dict(sorted(counts.items()))}
    (out_dir / "manifest.step7.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

