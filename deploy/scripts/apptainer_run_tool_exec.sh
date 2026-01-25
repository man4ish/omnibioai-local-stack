#!/usr/bin/env bash
set -euo pipefail

SIF="${1:?path to sif}"
PORT="${PORT:-8081}"

# Use writable tmp and a bind-mounted work dir
WORKDIR="${WORKDIR:-$PWD/work}"
mkdir -p "$WORKDIR"

apptainer run \
  --bind "$WORKDIR:/work" \
  --env TES_PORT="$PORT" \
  "$SIF"
