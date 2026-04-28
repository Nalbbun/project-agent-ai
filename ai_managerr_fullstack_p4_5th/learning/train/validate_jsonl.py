from __future__ import annotations

import argparse
import json
from pathlib import Path

import jsonschema


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", required=True)
    parser.add_argument("--schema", required=True)
    args = parser.parse_args()

    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    ok = 0
    total = 0
    for line_no, line in enumerate(Path(args.jsonl).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        total += 1
        obj = json.loads(line)
        try:
            jsonschema.validate(obj, schema)
            ok += 1
        except Exception as exc:
            print(f"[INVALID] line={line_no} error={exc}")
    print({"total": total, "valid": ok, "invalid": total - ok})


if __name__ == "__main__":
    main()
