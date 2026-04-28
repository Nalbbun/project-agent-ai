#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

BASE_MODEL_ROOT="${BASE_MODEL_ROOT:-/srv/llm/base}"
ADAPTER_ROOT="${ADAPTER_ROOT:-/srv/llm/adapters}"
MERGED_HF_ROOT="${MERGED_HF_ROOT:-/srv/llm/merged/hf}"
GGUF_ROOT="${GGUF_ROOT:-/srv/llm/merged/ollama}"
LLAMACPP_ROOT="${LLAMACPP_ROOT:-/opt/llama.cpp}"
QUANT_TYPE="${QUANT_TYPE:-Q4_K_M}"
MERGE_DTYPE="${MERGE_DTYPE:-float16}"
ROLES_CSV="${ROLES:-architect,dev-fe,dev-be,dev-db,qa,secops,pm,manager}"
SKIP_UNSUPPORTED="${SKIP_UNSUPPORTED:-1}"
ENABLE_EXAONE_GGUF="${ENABLE_EXAONE_GGUF:-0}"

CONVERT_SCRIPT="${LLAMACPP_ROOT}/convert_hf_to_gguf.py"
QUANT_BIN=""
if [[ -x "${LLAMACPP_ROOT}/build/bin/llama-quantize" ]]; then
  QUANT_BIN="${LLAMACPP_ROOT}/build/bin/llama-quantize"
elif [[ -x "${LLAMACPP_ROOT}/llama-quantize" ]]; then
  QUANT_BIN="${LLAMACPP_ROOT}/llama-quantize"
elif command -v llama-quantize >/dev/null 2>&1; then
  QUANT_BIN="$(command -v llama-quantize)"
fi

require_file() {
  local path="$1"
  if [[ ! -e "$path" ]]; then
    echo "[ERROR] missing required path: $path" >&2
    exit 1
  fi
}

role_to_base_rel() {
  case "$1" in
    pm|manager) echo "exaone/EXAONE-3.5-2.4B-Instruct" ;;
    architect|qa|secops) echo "qwen/Qwen2.5-3B-Instruct" ;;
    dev-fe|dev-be|dev-db) echo "qwen/Qwen2.5-Coder-1.5B-Instruct" ;;
    *) return 1 ;;
  esac
}

role_to_adapter_name() {
  case "$1" in
    architect) echo "architect-lora" ;;
    dev-fe) echo "dev-fe-lora" ;;
    dev-be) echo "dev-be-lora" ;;
    dev-db) echo "dev-db-lora" ;;
    pm) echo "pm-lora" ;;
    qa) echo "qa-lora" ;;
    secops) echo "secops-lora" ;;
    manager) echo "manager-lora" ;;
    *) return 1 ;;
  esac
}

role_requires_trust_remote_code() {
  case "$1" in
    pm|manager) echo "1" ;;
    *) echo "0" ;;
  esac
}

normalize_roles() {
  echo "$ROLES_CSV" | tr ',' ' '
}

convert_to_f16_gguf() {
  local merged_dir="$1"
  local out_f16="$2"
  require_file "$CONVERT_SCRIPT"
  local help_text
  help_text="$(python "$CONVERT_SCRIPT" -h 2>&1 || true)"

  if grep -q -- '--outfile' <<<"$help_text"; then
    python "$CONVERT_SCRIPT" "$merged_dir" --outfile "$out_f16" --outtype f16
  else
    echo "[ERROR] convert_hf_to_gguf.py in ${LLAMACPP_ROOT} does not expose --outfile. Update llama.cpp and retry." >&2
    exit 1
  fi
}

quantize_gguf() {
  local input_f16="$1"
  local output_quant="$2"
  if [[ -z "$QUANT_BIN" ]]; then
    echo "[WARN] llama-quantize not found. Keeping F16 GGUF only: $input_f16"
    return 0
  fi
  "$QUANT_BIN" "$input_f16" "$output_quant" "$QUANT_TYPE"
}

process_role() {
  local role="$1"
  local base_rel adapter_name base_path adapter_path merged_dir out_f16 out_quant trust_flag

  base_rel="$(role_to_base_rel "$role")"
  adapter_name="$(role_to_adapter_name "$role")"
  base_path="${BASE_MODEL_ROOT}/${base_rel}"
  adapter_path="${ADAPTER_ROOT}/${adapter_name}"

  if [[ "$role" =~ ^(pm|manager)$ && "$ENABLE_EXAONE_GGUF" != "1" ]]; then
    echo "[WARN] skipping ${role}: ENABLE_EXAONE_GGUF=1 is required to try EXAONE GGUF conversion."
    return 0
  fi

  require_file "$base_path"
  require_file "$adapter_path"

  merged_dir="${MERGED_HF_ROOT}/${role}-agent"
  out_f16="${GGUF_ROOT}/${role}-agent-f16.gguf"
  out_quant="${GGUF_ROOT}/${role}-agent.gguf"
  mkdir -p "$merged_dir" "$MERGED_HF_ROOT" "$GGUF_ROOT"

  echo "[INFO] role=${role} base=${base_path} adapter=${adapter_path}"

  trust_flag="$(role_requires_trust_remote_code "$role")"
  if [[ "$trust_flag" == "1" ]]; then
    python "${SCRIPT_DIR}/merge_peft_lora.py"       --base-model "$base_path"       --adapter "$adapter_path"       --output-dir "$merged_dir"       --dtype "$MERGE_DTYPE"       --trust-remote-code
  else
    python "${SCRIPT_DIR}/merge_peft_lora.py"       --base-model "$base_path"       --adapter "$adapter_path"       --output-dir "$merged_dir"       --dtype "$MERGE_DTYPE"
  fi

  convert_to_f16_gguf "$merged_dir" "$out_f16"
  quantize_gguf "$out_f16" "$out_quant"

  if [[ -f "$out_quant" ]]; then
    echo "[OK] quantized GGUF created: $out_quant"
  else
    echo "[OK] F16 GGUF created: $out_f16"
  fi
}

main() {
  local role failures=0
  for role in $(normalize_roles); do
    if ! process_role "$role"; then
      echo "[ERROR] failed role: $role" >&2
      failures=$((failures + 1))
      if [[ "$SKIP_UNSUPPORTED" != "1" ]]; then
        exit 1
      fi
    fi
  done

  if [[ "$failures" -gt 0 ]]; then
    echo "[WARN] completed with failures: $failures"
  else
    echo "[OK] all requested roles processed"
  fi
}

main "$@"
