#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

REGISTRATION_CONFIG_PATH="${REGISTRATION_CONFIG_PATH:-${PROJECT_ROOT}/configs/ollama_registration.local.yaml}"
MANIFEST_PATH="${MANIFEST_PATH:-${PROJECT_ROOT}/.tmp/ollama_registration_manifest.json}"
OLLAMA_BIN="${OLLAMA_BIN:-ollama}"
DRY_RUN="${DRY_RUN:-0}"
MERGE_ROLES="${MERGE_ROLES:-${ROLES:-architect,dev-fe,dev-be,dev-db,qa,secops,pm,manager}}"

export ROLES="$MERGE_ROLES"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "[DRY-RUN] merge/convert roles=${ROLES}"
fi

bash "${PROJECT_ROOT}/scripts/merge_lora_and_convert_to_gguf.sh"

REGISTRATION_CONFIG_PATH="$REGISTRATION_CONFIG_PATH" \
MANIFEST_PATH="$MANIFEST_PATH" \
OLLAMA_BIN="$OLLAMA_BIN" \
DRY_RUN="$DRY_RUN" \
bash "${PROJECT_ROOT}/serving/ollama/register_models.sh"

if [[ "$DRY_RUN" != "1" ]]; then
  echo "[INFO] registered models:"
  "$OLLAMA_BIN" list || true
fi

echo "[OK] merge -> gguf -> ollama registration completed"
