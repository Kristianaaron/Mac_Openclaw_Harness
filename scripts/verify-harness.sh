#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 -m py_compile "$REPO_ROOT/scripts/openclaw-tui-self-improvement.py"
zsh -n "$REPO_ROOT/openclaw-local-wrapper.zsh"
bash -n "$REPO_ROOT/scripts/install-openclaw-harness.sh"
bash -n "$REPO_ROOT/run-gemma-janq-openclaw-server.sh"
python3 "$REPO_ROOT/scripts/openclaw-tui-self-improvement.py" --openclaw-dir "${OPENCLAW_DIR:-$HOME/.openclaw}" --json >/tmp/openclaw-tui-self-improvement-canary.json
python3 -m json.tool "$REPO_ROOT/config/model-profiles.json" >/dev/null
python3 -m json.tool "$REPO_ROOT/openclaw-local-mlx-config.json" >/dev/null

echo "Harness verification passed."
