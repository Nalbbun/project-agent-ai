from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable

from .common import safe_json_load, schema_pass_rate, weighted_sum


def _run(cmd: list[str], cwd: str) -> float:
    try:
        completed = subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)
        return 1.0 if completed.returncode == 0 else 0.0
    except FileNotFoundError:
        return 0.0


def materialize_files(files: Iterable[Dict[str, str]], root: Path) -> None:
    for item in files:
        path = root / item["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(item["content"], encoding="utf-8")


def compute_dev_reward(completion_text: str, schema_path: str, build_cmd: list[str], test_cmd: list[str], lint_cmd: list[str] | None = None) -> Dict[str, Any]:
    pred = safe_json_load(completion_text)
    schema = schema_pass_rate(pred, schema_path)
    if not pred or "output" not in pred or "files" not in pred["output"]:
        return {"reward": 0.0, "details": {"schema": schema, "build": 0.0, "test": 0.0, "lint": 0.0, "has_tests": 0.0}}

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        materialize_files(pred["output"].get("files", []), root)
        materialize_files(pred["output"].get("tests", []), root)
        parts = {
            "schema": schema,
            "build": _run(build_cmd, td),
            "test": _run(test_cmd, td),
            "lint": _run(lint_cmd, td) if lint_cmd else 1.0,
            "has_tests": 1.0 if pred["output"].get("tests") else 0.2,
        }
    weights = {"schema": 0.15, "build": 0.35, "test": 0.30, "lint": 0.10, "has_tests": 0.10}
    result = weighted_sum(parts, weights)
    return {"reward": result.total, "details": result.details}
