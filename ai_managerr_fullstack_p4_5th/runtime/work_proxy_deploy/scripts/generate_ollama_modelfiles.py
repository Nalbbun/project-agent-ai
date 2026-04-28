from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_modelfile(gguf_path: Path, model_cfg: dict[str, Any]) -> str:
    lines = [f"FROM {gguf_path}"]
    system = (model_cfg.get("system") or "").strip()
    if system:
        escaped = system.replace('"', '\\"')
        lines.append(f'SYSTEM "{escaped}"')
    for key, value in (model_cfg.get("parameters") or {}).items():
        lines.append(f"PARAMETER {key} {value}")
    return "\n".join(lines) + "\n"


def resolve_gguf(paths_cfg: dict[str, Any], model_cfg: dict[str, Any]) -> Path | None:
    gguf_root = Path(paths_cfg["gguf_root"])
    primary = gguf_root / model_cfg["gguf_file"]
    if primary.exists():
        return primary
    fallback = model_cfg.get("fallback_gguf_file")
    if fallback:
        fb = gguf_root / fallback
        if fb.exists():
            return fb
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--manifest-out", required=True)
    args = parser.parse_args()

    cfg = load_yaml(Path(args.config))
    paths_cfg = cfg["paths"]
    modelfile_root = Path(paths_cfg["modelfile_root"])
    modelfile_root.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {"models": []}
    for role, model_cfg in (cfg.get("models") or {}).items():
        gguf_path = resolve_gguf(paths_cfg, model_cfg)
        if gguf_path is None:
            manifest["models"].append({
                "role": role,
                "name": model_cfg["name"],
                "status": "missing_gguf",
            })
            continue

        model_dir = modelfile_root / role
        model_dir.mkdir(parents=True, exist_ok=True)
        modelfile_path = model_dir / "Modelfile"
        modelfile_path.write_text(build_modelfile(gguf_path, model_cfg), encoding="utf-8")
        manifest["models"].append({
            "role": role,
            "name": model_cfg["name"],
            "status": "ready",
            "gguf_path": str(gguf_path),
            "modelfile_path": str(modelfile_path),
        })

    Path(args.manifest_out).write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
