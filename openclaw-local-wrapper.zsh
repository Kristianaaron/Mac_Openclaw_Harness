# Auto-start the local MLX backend before interactive OpenClaw commands.
# This file is also copied to ~/.zfunc/openclaw for zsh autoload.

local real_openclaw="/opt/homebrew/bin/openclaw"
local lab_dir="/Users/kristian/Documents/Codex/2026-04-25/hey-codex-are-you-able-to"
local log_dir="$HOME/.openclaw/logs"
local mlx_log="$log_dir/rapid-mlx-qwen-server.log"
local gateway_log="$log_dir/gateway-autostart.log"
local gateway_err="$log_dir/gateway-autostart.err.log"

case "${1:-}" in
  tui|terminal|chat|gateway|agent)
    export OPENCLAW_GATEWAY_TOKEN="${OPENCLAW_GATEWAY_TOKEN:-local-dev-token}"
    mkdir -p "$log_dir"
    if ! curl -fsS http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then
      echo "Starting local Qwen Rapid-MLX server..."
      (cd "$lab_dir" && nohup ./run-qwen-rapid-mlx-server.sh >"$mlx_log" 2>&1 &)
      local i
      for i in {1..90}; do
        if curl -fsS http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then
          break
        fi
        sleep 1
      done
    fi
    if [[ "${1:-}" != "gateway" ]] && ! curl -fsS "http://127.0.0.1:18789/health" >/dev/null 2>&1; then
      echo "Starting OpenClaw gateway..."
      nohup "$real_openclaw" gateway run --port 18789 --token "$OPENCLAW_GATEWAY_TOKEN" >"$gateway_log" 2>"$gateway_err" &
      local j
      for j in {1..30}; do
        if curl -fsS "http://127.0.0.1:18789/health" >/dev/null 2>&1 || lsof -nP -iTCP:18789 -sTCP:LISTEN >/dev/null 2>&1; then
          break
        fi
        sleep 1
      done
    fi
    ;;
esac

command "$real_openclaw" "$@"
