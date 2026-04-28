from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable

from .common import safe_json_load, schema_pass_rate, weighted_sum

DDL_FILE = "schema.sql"
INDEX_FILE = "indexes.sql"


def _run(cmd: list[str], cwd: str) -> float:
    try:
        completed = subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)
        return 1.0 if completed.returncode == 0 else 0.0
    except FileNotFoundError:
        return 0.0


def _write_lines(path: Path, lines: Iterable[str]) -> None:
    normalized = [line.strip() for line in lines if line and line.strip()]
    if not normalized:
        return
    content = "\n\n".join(
        stmt if stmt.rstrip().endswith(";") else f"{stmt};" for stmt in normalized
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + "\n", encoding="utf-8")


def materialize_dev_db_output(output: Dict[str, Any], root: Path) -> Dict[str, Path]:
    migration = output.get("migration", {})
    migration_file = migration.get("file", "migrations/V001__generated.sql")
    ddl_path = root / DDL_FILE
    idx_path = root / INDEX_FILE
    migration_path = root / migration_file

    ddl = output.get("ddl", [])
    indexes = output.get("indexes", [])

    _write_lines(ddl_path, ddl)
    _write_lines(idx_path, indexes)

    merged_sql: list[str] = []
    merged_sql.extend(ddl)
    merged_sql.extend(indexes)
    _write_lines(migration_path, merged_sql)

    return {
        "ddl_path": ddl_path,
        "indexes_path": idx_path,
        "migration_path": migration_path,
    }


def _ddl_presence_score(output: Dict[str, Any]) -> float:
    ddl = output.get("ddl", [])
    if not isinstance(ddl, list) or not ddl:
        return 0.0
    create_hits = sum(
        1 for stmt in ddl if isinstance(stmt, str) and "create table" in stmt.lower()
    )
    return min(1.0, 0.4 + 0.3 * create_hits)


def _index_score(output: Dict[str, Any]) -> float:
    indexes = output.get("indexes", [])
    if not isinstance(indexes, list):
        return 0.0
    if not indexes:
        return 0.4
    valid_hits = sum(
        1 for stmt in indexes if isinstance(stmt, str) and "create index" in stmt.lower()
    )
    return min(1.0, valid_hits / max(1, len(indexes)))


def _migration_score(output: Dict[str, Any]) -> float:
    migration = output.get("migration", {})
    if not isinstance(migration, dict):
        return 0.0
    tool = str(migration.get("tool", "")).strip().lower()
    file_name = str(migration.get("file", "")).strip()
    if not tool or not file_name:
        return 0.0
    tool_ok = tool in {"flyway", "liquibase", "dbmate", "goose", "alembic"}
    ext_ok = file_name.endswith((".sql", ".xml", ".yaml", ".yml", ".json"))
    return 1.0 if tool_ok and ext_ok else 0.5 if tool_ok or ext_ok else 0.0


def compute_dev_db_reward(
    completion_text: str,
    schema_path: str,
    build_cmd: list[str],
    test_cmd: list[str],
    lint_cmd: list[str] | None = None,
) -> Dict[str, Any]:
    pred = safe_json_load(completion_text)
    schema = schema_pass_rate(pred, schema_path)
    if not pred or "output" not in pred:
        return {
            "reward": 0.0,
            "details": {
                "schema": schema,
                "build": 0.0,
                "test": 0.0,
                "lint": 0.0,
                "ddl": 0.0,
                "indexes": 0.0,
                "migration": 0.0,
            },
        }

    output = pred["output"]
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        materialize_dev_db_output(output, root)
        parts = {
            "schema": schema,
            "build": _run(build_cmd, td),
            "test": _run(test_cmd, td),
            "lint": _run(lint_cmd, td) if lint_cmd else 1.0,
            "ddl": _ddl_presence_score(output),
            "indexes": _index_score(output),
            "migration": _migration_score(output),
        }

    weights = {
        "schema": 0.15,
        "build": 0.20,
        "test": 0.25,
        "lint": 0.10,
        "ddl": 0.15,
        "indexes": 0.05,
        "migration": 0.10,
    }
    result = weighted_sum(parts, weights)
    return {"reward": result.total, "details": result.details}
