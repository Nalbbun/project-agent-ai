#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$ROOT_DIR/work/dist"
TS="$(date -u +%Y%m%d-%H%M%S)"
OUT="$DIST_DIR/project-agent-ai-applied-source-$TS.tar.gz"

mkdir -p "$DIST_DIR"

cd "$ROOT_DIR"
tar -czf "$OUT" \
  source \
  DOC/source_project_analysis.md \
  DOC/work_step_timeline_replan.md \
  DOC/applied_source_package_guide.md

echo "Created: $OUT"
