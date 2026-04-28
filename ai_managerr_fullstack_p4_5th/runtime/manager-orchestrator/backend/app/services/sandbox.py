from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from app.core.config import get_settings

settings = get_settings()


class SandboxExecutor:
    """Best-effort isolated command runner with local/docker modes."""

    def __init__(self, timeout_seconds: int | None = None):
        self.timeout_seconds = timeout_seconds or settings.tool_command_timeout_seconds
        self.mode = getattr(settings, "runner_sandbox_mode", "local")
        self.default_image = getattr(settings, "runner_sandbox_docker_image", "manager-orchestrator-runner-python:latest")
        self.image_map = getattr(settings, "runner_sandbox_docker_image_map", {"default": self.default_image})
        self.network_enabled = getattr(settings, "runner_sandbox_network_enabled", False)

    def image_for_stack(self, stack: str | None) -> str:
        if stack and stack in self.image_map:
            return self.image_map[stack]
        if stack:
            prefix = stack.split("-", 1)[0]
            if prefix in self.image_map:
                return self.image_map[prefix]
        return self.image_map.get("default", self.default_image)

    def run(self, command: str, workspace: Path, stack: str | None = None) -> dict[str, Any]:
        if self.mode == "docker" and shutil.which("docker"):
            return self._run_docker(command, workspace, stack)
        return self._run_local(command, workspace, stack)

    def _run_local(self, command: str, workspace: Path, stack: str | None) -> dict[str, Any]:
        sandbox_home = workspace / ".sandbox_home"
        sandbox_tmp = workspace / ".sandbox_tmp"
        sandbox_home.mkdir(parents=True, exist_ok=True)
        sandbox_tmp.mkdir(parents=True, exist_ok=True)
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(sandbox_home),
            "TMPDIR": str(sandbox_tmp),
            "TEMP": str(sandbox_tmp),
            "TMP": str(sandbox_tmp),
            "PYTHONUNBUFFERED": "1",
            "CI": "1",
            "RUNNER_SANDBOX_MODE": "local",
        }
        return self._execute(command, workspace, env, "local", stack)

    def _run_docker(self, command: str, workspace: Path, stack: str | None) -> dict[str, Any]:
        image = self.image_for_stack(stack)
        docker_cmd = [
            "docker", "run", "--rm",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit", str(getattr(settings, "runner_sandbox_docker_pids_limit", 256)),
            "--memory", str(getattr(settings, "runner_sandbox_docker_memory", "1024m")),
            "--cpus", str(getattr(settings, "runner_sandbox_docker_cpus", "1.0")),
            "--user", str(getattr(settings, "runner_sandbox_docker_user", "65532:65532")),
            "-v", f"{workspace.resolve()}:/workspace:rw",
            "-w", "/workspace",
            "--tmpfs", "/tmp:rw,nosuid,nodev,noexec,size=256m",
            "--tmpfs", "/home/sandbox:rw,nosuid,nodev,size=64m",
            "-e", "HOME=/home/sandbox",
            "-e", "TMPDIR=/tmp",
            "-e", "CI=1",
            "-e", "RUNNER_SANDBOX_MODE=docker",
        ]
        if getattr(settings, "runner_sandbox_docker_read_only", True):
            docker_cmd.append("--read-only")
        if not self.network_enabled:
            docker_cmd += ["--network", "none"]
        docker_cmd += [image, "sh", "-lc", command]
        started = time.perf_counter()
        try:
            proc = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=self.timeout_seconds)
            return {
                "command": command,
                "stack": stack,
                "sandbox_mode": "docker",
                "sandbox_image": image,
                "network_enabled": self.network_enabled,
                "exit_code": proc.returncode,
                "stdout": (proc.stdout or "")[-4000:],
                "stderr": (proc.stderr or "")[-4000:],
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "status": "pass" if proc.returncode == 0 else "fail",
            }
        except subprocess.TimeoutExpired as exc:
            stdout = (exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
            stderr = (exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""))
            return {
                "command": command,
                "stack": stack,
                "sandbox_mode": "docker",
                "sandbox_image": image,
                "network_enabled": self.network_enabled,
                "exit_code": None,
                "stdout": stdout[-4000:],
                "stderr": (stderr + f"\nTimed out after {self.timeout_seconds}s")[-4000:],
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "status": "fail",
            }

    def _execute(self, command: str, workspace: Path, env: dict[str, str], sandbox_mode: str, stack: str | None) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            proc = subprocess.run(command, cwd=workspace, shell=True, capture_output=True, text=True, timeout=self.timeout_seconds, env=env)
            return {
                "command": command,
                "stack": stack,
                "sandbox_mode": sandbox_mode,
                "network_enabled": False,
                "exit_code": proc.returncode,
                "stdout": (proc.stdout or "")[-4000:],
                "stderr": (proc.stderr or "")[-4000:],
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "status": "pass" if proc.returncode == 0 else "fail",
            }
        except subprocess.TimeoutExpired as exc:
            stdout = (exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
            stderr = (exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""))
            return {
                "command": command,
                "stack": stack,
                "sandbox_mode": sandbox_mode,
                "network_enabled": False,
                "exit_code": None,
                "stdout": stdout[-4000:],
                "stderr": (stderr + f"\nTimed out after {self.timeout_seconds}s")[-4000:],
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "status": "fail",
            }
