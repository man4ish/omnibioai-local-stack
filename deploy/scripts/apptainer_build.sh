#!/usr/bin/env bash
set -euo pipefail

OUT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../hpc" && pwd)"
mkdir -p "$OUT"

IMAGES=(
  "docker://man4ish/omnibioai-tool-exec:latest"
  "docker://man4ish/omnibioai-workflow-service:latest"
  "docker://ollama/ollama:latest"
)

for img in "${IMAGES[@]}"; do
  name="$(echo "$img" | sed 's#docker://##' | tr '/:' '__')"
  echo "[apptainer] building $name.sif"
  apptainer build "$OUT/$name.sif" "$img"
done
echo "[apptainer] Done: $OUT"
