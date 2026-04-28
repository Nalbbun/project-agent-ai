#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MODEL_ROOT="${OLLAMA_GGUF_ROOT:-/srv/llm/merged/ollama}"

require_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "[ERROR] Missing GGUF file: $file" >&2
    exit 1
  fi
}

create_model() {
  local name="$1"
  local modelfile="$2"
  echo "[INFO] Creating model: $name"
  ollama create "$name" -f "$modelfile"
}

for gguf in   "$MODEL_ROOT/pm-agent.gguf"   "$MODEL_ROOT/architect-agent.gguf"   "$MODEL_ROOT/dev-fe-agent.gguf"   "$MODEL_ROOT/dev-be-agent.gguf"   "$MODEL_ROOT/dev-db-agent.gguf"   "$MODEL_ROOT/qa-agent.gguf"   "$MODEL_ROOT/secops-agent.gguf"   "$MODEL_ROOT/manager-agent.gguf"; do
  require_file "$gguf"
done

create_model pm-agent "$SCRIPT_DIR/Modelfile.pm"
create_model architect-agent "$SCRIPT_DIR/Modelfile.architect"
create_model dev-fe-agent "$SCRIPT_DIR/Modelfile.dev-fe"
create_model dev-be-agent "$SCRIPT_DIR/Modelfile.dev-be"
create_model dev-db-agent "$SCRIPT_DIR/Modelfile.dev-db"
create_model qa-agent "$SCRIPT_DIR/Modelfile.qa"
create_model secops-agent "$SCRIPT_DIR/Modelfile.secops"
create_model manager-agent "$SCRIPT_DIR/Modelfile.manager"

echo "[INFO] Done. Registered models:"
ollama list
