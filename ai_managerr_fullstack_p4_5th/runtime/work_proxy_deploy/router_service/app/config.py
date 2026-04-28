from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class RouterConfigError(ValueError):
    pass


REQUIRED_ROOT_KEYS = {"router", "backends", "routes"}


def load_router_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise RouterConfigError(f"router config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    missing = REQUIRED_ROOT_KEYS - set(data.keys())
    if missing:
        raise RouterConfigError(f"router config missing keys: {', '.join(sorted(missing))}")

    router = data.get("router") or {}
    if not isinstance(data["backends"], dict) or not data["backends"]:
        raise RouterConfigError("router.backends must be a non-empty object")
    if not isinstance(data["routes"], dict) or not data["routes"]:
        raise RouterConfigError("router.routes must be a non-empty object")
    if not router.get("request_role_fields"):
        raise RouterConfigError("router.request_role_fields must not be empty")

    for backend_name, backend in data["backends"].items():
        if not backend.get("base_url"):
            raise RouterConfigError(f"backend '{backend_name}' missing base_url")
        for field_name in ("timeout_seconds", "connect_timeout_seconds", "max_retries"):
            if field_name in backend and not isinstance(backend[field_name], int):
                raise RouterConfigError(f"backend '{backend_name}' field '{field_name}' must be integer")

    for route_name, route in data["routes"].items():
        backend_name = route.get("backend")
        if not backend_name:
            raise RouterConfigError(f"route '{route_name}' missing backend")
        if backend_name not in data["backends"]:
            raise RouterConfigError(
                f"route '{route_name}' references unknown backend '{backend_name}'"
            )
        if not route.get("target_model"):
            raise RouterConfigError(f"route '{route_name}' missing target_model")
        for idx, fb in enumerate(route.get("fallback", []) or []):
            fb_backend = fb.get("backend")
            if fb_backend not in data["backends"]:
                raise RouterConfigError(
                    f"route '{route_name}' fallback[{idx}] references unknown backend '{fb_backend}'"
                )

    return data
