#!/usr/bin/env bash
set -euo pipefail
DIR=$(cd -- "$(dirname -- "$0")" && pwd)
docker build -t manager-orchestrator-runner-python:latest "$DIR/python"
docker build -t manager-orchestrator-runner-node:latest "$DIR/node"
docker build -t manager-orchestrator-runner-java:latest "$DIR/java"
