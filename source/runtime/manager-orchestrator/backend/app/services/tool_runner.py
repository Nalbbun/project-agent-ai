from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services.sandbox import SandboxExecutor

settings = get_settings()


class ToolRunner:
    def __init__(self, artifact_dir: str | Path):
        self.artifact_dir = Path(artifact_dir)
        self.timeout_seconds = settings.tool_command_timeout_seconds
        self.sandbox = SandboxExecutor(self.timeout_seconds)

    def run_build(self, run_id: str, step_phase: str, payload: dict[str, Any]) -> dict[str, Any]:
        work = self._materialize(run_id, step_phase, payload)
        stack = self._detect_stack(work["root_workspace"])
        report = self._execute_candidates(
            tool="build",
            phase=step_phase,
            workspace=work["root_workspace"],
            stack=stack,
            candidates=self._build_candidates(stack, work["root_workspace"]),
        )
        report["materialized_files"] = work["materialized_files"]
        return report

    def run_test(self, run_id: str, step_phase: str, payload: dict[str, Any]) -> dict[str, Any]:
        work = self._materialize(run_id, step_phase, payload)
        stack = self._detect_stack(work["root_workspace"])
        report = self._execute_candidates(
            tool="test",
            phase=step_phase,
            workspace=work["root_workspace"],
            stack=stack,
            candidates=self._test_candidates(stack, work["root_workspace"]),
        )
        report["checklist_test_case_count"] = len(payload.get("test_cases") or [])
        return report

    def run_lint(self, run_id: str, step_phase: str, payload: dict[str, Any]) -> dict[str, Any]:
        work = self._materialize(run_id, step_phase, payload)
        stack = self._detect_stack(work["root_workspace"])
        report = self._execute_candidates(
            tool="lint",
            phase=step_phase,
            workspace=work["root_workspace"],
            stack=stack,
            candidates=self._lint_candidates(stack, work["root_workspace"]),
        )
        report["materialized_files"] = work["materialized_files"]
        return report

    def run_type(self, run_id: str, step_phase: str, payload: dict[str, Any]) -> dict[str, Any]:
        work = self._materialize(run_id, step_phase, payload)
        stack = self._detect_stack(work["root_workspace"])
        report = self._execute_candidates(
            tool="type",
            phase=step_phase,
            workspace=work["root_workspace"],
            stack=stack,
            candidates=self._type_candidates(stack, work["root_workspace"]),
        )
        return report

    def run_scan(self, run_id: str, step_phase: str, payload: dict[str, Any]) -> dict[str, Any]:
        work = self._materialize(run_id, step_phase, payload)
        stack = self._detect_stack(work["root_workspace"])
        report = self._execute_candidates(
            tool="scan",
            phase=step_phase,
            workspace=work["root_workspace"],
            stack=stack,
            candidates=self._scan_candidates(stack, work["root_workspace"]),
        )
        report["secret_findings"] = self._secret_scan(work["root_workspace"])
        report["dependency_files"] = self._dependency_files(work["root_workspace"])
        if report["secret_findings"] and report["status"] in {"pass", "skipped"}:
            report["status"] = "warn"
        return report

    def _materialize(self, run_id: str, step_phase: str, payload: dict[str, Any]) -> dict[str, Any]:
        run_root = self.artifact_dir / "workspaces" / run_id / "workspace"
        step_root = self.artifact_dir / "workspaces" / run_id / "steps" / step_phase
        run_root.mkdir(parents=True, exist_ok=True)
        step_root.mkdir(parents=True, exist_ok=True)
        written: list[str] = []
        for target_root in (step_root, run_root):
            written.extend(self._write_payload_to_workspace(target_root, payload))
        return {
            "root_workspace": run_root,
            "step_workspace": step_root,
            "materialized_files": sorted(set(written)),
        }

    def _write_payload_to_workspace(self, workspace: Path, payload: dict[str, Any]) -> list[str]:
        written: list[str] = []
        for item in payload.get("files", []) + payload.get("tests", []):
            path = (item or {}).get("path")
            content = (item or {}).get("content", "")
            if not path:
                continue
            file_path = workspace / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(str(content), encoding="utf-8")
            written.append(path)
        ddl = payload.get("ddl") or []
        if ddl:
            (workspace / "schema.sql").write_text("\n\n".join(str(x) for x in ddl), encoding="utf-8")
            written.append("schema.sql")
        indexes = payload.get("indexes") or []
        if indexes:
            (workspace / "indexes.sql").write_text("\n".join(str(x) for x in indexes), encoding="utf-8")
            written.append("indexes.sql")
        migration = payload.get("migration") or {}
        if migration:
            migration_name = migration.get("file", "migration.sql")
            migration_content = migration.get("content") or json.dumps(migration, ensure_ascii=False, indent=2)
            file_path = workspace / migration_name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(str(migration_content), encoding="utf-8")
            written.append(migration_name)
        return written

    def _execute_candidates(self, tool: str, phase: str, workspace: Path, stack: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        report = {
            "tool": tool,
            "phase": phase,
            "workspace": str(workspace),
            "stack": stack,
            "status": "skipped",
            "executions": [],
            "detail": "no runnable command detected",
        }
        for candidate in candidates:
            if not self._is_candidate_available(candidate, workspace):
                continue
            result = self._run_command(candidate["command"], workspace, stack)
            result["name"] = candidate["name"]
            report["executions"].append(result)
            report["status"] = self._status_from_result(result)
            report["detail"] = candidate.get("detail") or candidate["name"]
            if result["status"] in {"pass", "warn"}:
                break
        return report

    def _build_candidates(self, stack: str, workspace: Path) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        if stack == "python":
            candidates.append({
                "name": "python-compileall",
                "command": f'"{sys.executable}" -m compileall .',
                "detail": "python source compilation",
            })
        if stack == "node":
            candidates.append({"name": "npm-build", "command": "npm run build --if-present", "requires": "npm"})
        if stack == "java-maven":
            candidates.append({"name": "maven-package", "command": "mvn -q -DskipTests package", "requires": "mvn"})
        if stack == "java-gradle":
            cmd = "./gradlew build -x test" if (workspace / "gradlew").exists() else "gradle build -x test"
            candidates.append({"name": "gradle-build", "command": cmd, "requires": "./gradlew" if (workspace / "gradlew").exists() else "gradle"})
        return candidates

    def _test_candidates(self, stack: str, workspace: Path) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        if stack == "python" and list(workspace.rglob("test_*.py")):
            candidates.append({"name": "pytest", "command": "pytest -q", "requires": "pytest"})
        if stack == "node":
            candidates.append({"name": "npm-test", "command": "npm test -- --runInBand", "requires": "npm"})
            candidates.append({"name": "npm-test-if-present", "command": "npm run test --if-present", "requires": "npm"})
        if stack == "java-maven":
            candidates.append({"name": "maven-test", "command": "mvn -q test", "requires": "mvn"})
        if stack == "java-gradle":
            cmd = "./gradlew test" if (workspace / "gradlew").exists() else "gradle test"
            candidates.append({"name": "gradle-test", "command": cmd, "requires": "./gradlew" if (workspace / "gradlew").exists() else "gradle"})
        return candidates

    def _lint_candidates(self, stack: str, workspace: Path) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        if stack == "python":
            if shutil.which("ruff"):
                candidates.append({"name": "ruff", "command": "ruff check .", "requires": "ruff"})
            if list(workspace.rglob("*.py")):
                candidates.append({"name": "python-syntax-check", "command": self._python_syntax_command(), "detail": "py_compile syntax check"})
        if stack == "node":
            candidates.append({"name": "npm-lint", "command": "npm run lint --if-present", "requires": "npm"})
        return candidates

    def _type_candidates(self, stack: str, workspace: Path) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        if stack == "python" and shutil.which("mypy"):
            candidates.append({"name": "mypy", "command": "mypy .", "requires": "mypy"})
        if stack == "node" and ((workspace / "tsconfig.json").exists() or list(workspace.rglob("*.ts")) or list(workspace.rglob("*.tsx"))):
            if (workspace / "package.json").exists():
                candidates.append({"name": "npm-typecheck", "command": "npm run typecheck --if-present", "requires": "npm"})
            if shutil.which("tsc"):
                candidates.append({"name": "tsc", "command": "tsc --noEmit", "requires": "tsc"})
        return candidates

    def _scan_candidates(self, stack: str, workspace: Path) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        if shutil.which("semgrep"):
            candidates.append({"name": "semgrep-auto", "command": "semgrep --config auto --json .", "requires": "semgrep"})
        if stack == "python" and shutil.which("bandit"):
            candidates.append({"name": "bandit", "command": "bandit -r . -f json", "requires": "bandit"})
        return candidates

    def _run_command(self, command: str, workspace: Path, stack: str) -> dict[str, Any]:
        return self.sandbox.run(command, workspace, stack=stack)

    def _detect_stack(self, workspace: Path) -> str:
        if (workspace / "package.json").exists():
            return "node"
        if (workspace / "pom.xml").exists():
            return "java-maven"
        if (workspace / "gradlew").exists() or (workspace / "build.gradle").exists() or (workspace / "build.gradle.kts").exists():
            return "java-gradle"
        if (workspace / "pyproject.toml").exists() or (workspace / "requirements.txt").exists() or list(workspace.rglob("*.py")):
            return "python"
        if list(workspace.rglob("*.sql")):
            return "sql"
        return "unknown"

    def _is_candidate_available(self, candidate: dict[str, Any], workspace: Path) -> bool:
        required = candidate.get("requires")
        if not required:
            return True
        if required == "./gradlew":
            return (workspace / "gradlew").exists()
        return shutil.which(required) is not None

    @staticmethod
    def _status_from_result(result: dict[str, Any]) -> str:
        return "pass" if result["status"] == "pass" else "fail"

    def _secret_scan(self, workspace: Path) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        pattern = re.compile(r"(api[_-]?key|password|secret|token)\s*[:=]\s*[\"']?[^\s\"']+[\"']?", re.IGNORECASE)
        for file_path in workspace.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".jar", ".class", ".zip"}:
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except Exception:
                continue
            for idx, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line):
                    findings.append({"file": str(file_path.relative_to(workspace)), "line": idx, "match": line[:240]})
        return findings[:200]

    def _dependency_files(self, workspace: Path) -> list[str]:
        names = {"package.json", "package-lock.json", "requirements.txt", "pyproject.toml", "pom.xml", "build.gradle", "build.gradle.kts"}
        found: list[str] = []
        for file_path in workspace.rglob("*"):
            if file_path.is_file() and file_path.name in names:
                found.append(str(file_path.relative_to(workspace)))
        return sorted(found)

    @staticmethod
    def _python_syntax_command() -> str:
        script = (
            "import pathlib, py_compile, sys; "
            "errors=[]; "
            "files=list(pathlib.Path('.').rglob('*.py')); "
            "\nfor p in files:\n"
            "    try:\n"
            "        py_compile.compile(str(p), doraise=True)\n"
            "    except Exception as exc:\n"
            "        errors.append(f'{p}:{exc}')\n"
            "print(f'checked={len(files)}');\n"
            "print('\\n'.join(errors[:50]));\n"
            "sys.exit(0 if not errors else 1)"
        )
        return f'"{sys.executable}" -c "{script}"'
