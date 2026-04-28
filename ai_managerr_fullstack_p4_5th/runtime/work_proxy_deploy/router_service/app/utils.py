from __future__ import annotations

from copy import deepcopy
from typing import Any


def get_nested(data: Any, path: str) -> Any:
    current = data
    for part in path.split('.'):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def delete_nested(data: dict[str, Any], path: str) -> None:
    parts = path.split('.')
    current: Any = data
    parents: list[tuple[dict[str, Any], str]] = []
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        parents.append((current, part))
        current = current[part]
    if isinstance(current, dict):
        current.pop(parts[-1], None)

    # prune empty dicts bottom-up
    for parent, key in reversed(parents):
        child = parent.get(key)
        if isinstance(child, dict) and not child:
            parent.pop(key, None)
        else:
            break


def merged_generation(defaults: dict[str, Any], overrides: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(defaults or {})
    for key, value in (overrides or {}).items():
        merged[key] = value
    for key, value in request.items():
        if key in merged and value is not None:
            merged[key] = value
    return merged
