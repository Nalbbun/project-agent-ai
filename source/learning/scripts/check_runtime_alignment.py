#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[3]
LEARNING = ROOT / "source" / "learning"
RUNTIME = ROOT / "source" / "runtime"


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def runtime_required_keys(path: Path) -> dict[str, list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "REQUIRED_KEYS":
                    return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "REQUIRED_KEYS":
            return ast.literal_eval(node.value)
    raise ValueError(f"REQUIRED_KEYS not found: {path}")


def schema_output_required(path: Path) -> list[str]:
    schema = load_json(path)
    output = schema.get("properties", {}).get("output", {})
    return list(output.get("required", []))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check runtime/router/learning role alignment.")
    parser.add_argument("--agents", default=str(RUNTIME / "manager-orchestrator" / "config" / "agents.yaml"))
    parser.add_argument("--router", default=str(RUNTIME / "work_proxy_deploy" / "configs" / "vllm_request_router.local.yaml"))
    parser.add_argument("--adapters", default=str(LEARNING / "configs" / "adapter_registry.local.yaml"))
    parser.add_argument("--validator", default=str(RUNTIME / "manager-orchestrator" / "backend" / "app" / "services" / "schema_validator.py"))
    parser.add_argument("--schemas", default=str(LEARNING / "schemas"))
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    agents = load_yaml(Path(args.agents)).get("agents", [])
    routes = load_yaml(Path(args.router)).get("routes", {})
    adapters = load_yaml(Path(args.adapters)).get("adapters", {})
    required_by_role = runtime_required_keys(Path(args.validator))
    schema_dir = Path(args.schemas)

    findings: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    active_agents = [agent for agent in agents if agent.get("active", True)]
    for agent in active_agents:
        code = agent["code"]
        role = agent["role"]
        adapter = agent.get("adapter")
        route = routes.get(agent.get("router_role") or role)
        schema_path = schema_dir / f"{role}.schema.json"
        schema_required = schema_output_required(schema_path) if schema_path.exists() else []
        runtime_required = required_by_role.get(role, [])

        checks = {
            "adapter_registered": bool(adapter and adapter in adapters),
            "router_route_present": bool(route),
            "router_target_matches_adapter": bool(route and route.get("target_model") == adapter),
            "schema_present": schema_path.exists(),
            "schema_required_matches_runtime": set(schema_required) == set(runtime_required),
        }
        for check, ok in checks.items():
            if not ok:
                findings.append({"agent_code": code, "role": role, "check": check})
        rows.append({
            "agent_code": code,
            "role": role,
            "prompt_key": agent.get("prompt_key"),
            "adapter": adapter,
            "router_backend": route.get("backend") if route else None,
            "router_target_model": route.get("target_model") if route else None,
            "runtime_required_keys": runtime_required,
            "schema_required_keys": schema_required,
            "checks": checks,
        })

    report = {"ok": not findings, "checked_agents": len(active_agents), "findings": findings, "rows": rows}
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "checked_agents": report["checked_agents"], "finding_count": len(findings)}, ensure_ascii=False))
    if findings:
        for finding in findings:
            print(f"[MISALIGN] {finding['agent_code']} {finding['role']} {finding['check']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
