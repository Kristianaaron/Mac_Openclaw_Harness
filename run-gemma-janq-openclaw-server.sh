#!/usr/bin/env bash
set -euo pipefail

MODEL_HELPER="${OPENCLAW_MODEL_HELPER:-$HOME/.openclaw/bin/openclaw-model-profile}"

if [[ ! -x "$MODEL_HELPER" ]]; then
  echo "Missing OpenClaw model helper: $MODEL_HELPER" >&2
  echo "Run ./scripts/install-openclaw-harness.sh first, or install the current OpenClaw runtime helpers." >&2
  exit 1
fi

exec "$MODEL_HELPER" exec-server
