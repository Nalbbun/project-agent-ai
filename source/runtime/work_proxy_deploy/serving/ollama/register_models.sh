#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
REGISTRATION_CONFIG_PATH="${REGISTRATION_CONFIG_PATH:-${PROJECT_ROOT}/configs/ollama_registration.local.yaml}"
MANIFEST_PATH="${MANIFEST_PATH:-${PROJECT_ROOT}/.tmp/ollama_registration_manifest.json}"
OLLAMA_BIN="${OLLAMA_BIN:-ollama}"
DRY_RUN="${DRY_RUN:-0}"

mkdir -p "$(dirname -- "$MANIFEST_PATH")"
python "${PROJECT_ROOT}/scripts/generate_ollama_modelfiles.py" \
  --config "$REGISTRATION_CONFIG_PATH" \
  --manifest-out "$MANIFEST_PATH"

python - "$MANIFEST_PATH" <<'PY' | while IFS=$'\t' read -r name modelfile status; do
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
for item in manifest['models']:
    if item['status'] == 'ready':
        print(f"{item['name']}\t{item['modelfile_path']}\t{item['status']}")
PY
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[DRY-RUN] ${OLLAMA_BIN} create ${name} -f ${modelfile}"
  else
    echo "[INFO] registering ${name} from ${modelfile}"
    "$OLLAMA_BIN" create "$name" -f "$modelfile"
  fi
done

echo "[OK] registration flow complete: ${MANIFEST_PATH}"
