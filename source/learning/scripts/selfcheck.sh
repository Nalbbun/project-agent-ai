#!/usr/bin/env bash
set -euo pipefail

python -m compileall rewards train

if command -v ruff >/dev/null 2>&1; then
  ruff check rewards train
elif python -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('ruff') else 1)" >/dev/null 2>&1; then
  python -m ruff check rewards train
else
  echo "[WARN] ruff is not installed in the current environment. Skipping lint step."
fi

for role in architect dev-be dev-db dev-fe manager pm qa secops; do
  python train/validate_jsonl.py --jsonl data_examples/${role}/${role}.train.sample.jsonl --schema schemas/${role}.schema.json
  python train/validate_jsonl.py --jsonl data_examples/${role}/${role}.valid.sample.jsonl --schema schemas/${role}.schema.json
done

echo "[OK] self-check completed"
