#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENCLAW_DIR="${OPENCLAW_DIR:-$HOME/.openclaw}"
ZFUNC_DIR="${ZFUNC_DIR:-$HOME/.zfunc}"
WRAPPER_REPLACED=0

install_file() {
  local source="$1"
  local target="$2"
  local mode="${3:-644}"
  mkdir -p "$(dirname "$target")"
  if [[ -f "$target" ]]; then
    cp "$target" "$target.bak.$(date +%Y%m%d-%H%M%S)"
  fi
  cp "$source" "$target"
  chmod "$mode" "$target"
  echo "installed $target"
}

if [[ -f "$ZFUNC_DIR/openclaw" && "${OPENCLAW_INSTALL_REPLACE_WRAPPER:-0}" != "1" ]]; then
  install_file "$REPO_ROOT/openclaw-local-wrapper.zsh" "$ZFUNC_DIR/openclaw-tui-harness" 755
  echo "kept existing $ZFUNC_DIR/openclaw"
  echo "set OPENCLAW_INSTALL_REPLACE_WRAPPER=1 to replace it after review"
else
  install_file "$REPO_ROOT/openclaw-local-wrapper.zsh" "$ZFUNC_DIR/openclaw" 755
  WRAPPER_REPLACED=1
fi
install_file "$REPO_ROOT/scripts/openclaw-tui-self-improvement.py" "$OPENCLAW_DIR/bin/openclaw-tui-self-improvement" 755
install_file "$REPO_ROOT/config/model-profiles.json" "$OPENCLAW_DIR/model-profiles.json" 600

if [[ -f "$OPENCLAW_DIR/openclaw.json" ]]; then
  echo "kept existing $OPENCLAW_DIR/openclaw.json"
  if [[ -x "$OPENCLAW_DIR/bin/openclaw-model-profile" ]]; then
    "$OPENCLAW_DIR/bin/openclaw-model-profile" sync-config >/dev/null
    echo "synced active model/provider from model profile"
  else
    echo "model-profile helper missing; sample config remains at $REPO_ROOT/openclaw-local-mlx-config.json"
  fi
else
  install_file "$REPO_ROOT/openclaw-local-mlx-config.json" "$OPENCLAW_DIR/openclaw.json" 600
fi

echo
echo "OpenClaw TUI harness installed."
if [[ "$WRAPPER_REPLACED" == "1" ]]; then
  echo "Run: openclaw doctor"
  echo "Then: openclaw tui"
else
  echo "Run: $OPENCLAW_DIR/bin/openclaw-tui-self-improvement review"
  echo "Active wrapper was preserved; review $ZFUNC_DIR/openclaw-tui-harness before replacing $ZFUNC_DIR/openclaw."
fi
