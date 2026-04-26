#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_REPO="${MODEL_REPO:-unsloth/Qwen3.6-27B-UD-MLX-6bit}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"

MLX_SERVER="${MLX_SERVER:-$ROOT/.venv-mlx312/bin/mlx_lm.server}"

exec "$MLX_SERVER" \
  --model "$MODEL_REPO" \
  --host "$HOST" \
  --port "$PORT" \
  --temp "${TEMP:-0.2}" \
  --top-p "${TOP_P:-0.8}" \
  --top-k "${TOP_K:-20}" \
  --max-tokens "${MAX_TOKENS:-4096}" \
  --prefill-step-size "${PREFILL_STEP_SIZE:-1024}" \
  --decode-concurrency "${DECODE_CONCURRENCY:-1}" \
  --prompt-concurrency "${PROMPT_CONCURRENCY:-1}" \
  --prompt-cache-size "${PROMPT_CACHE_SIZE:-1}" \
  --prompt-cache-bytes "${PROMPT_CACHE_BYTES:-2147483648}" \
  --chat-template-args '{"enable_thinking":false}'
