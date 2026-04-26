#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
MODEL="${MODEL:-qwen3.6-27b}"

exec rapid-mlx serve "$MODEL" \
  --host "$HOST" \
  --port "$PORT" \
  --max-num-seqs "${MAX_NUM_SEQS:-16}" \
  --prefill-batch-size "${PREFILL_BATCH_SIZE:-16}" \
  --completion-batch-size "${COMPLETION_BATCH_SIZE:-32}" \
  --continuous-batching \
  --kv-cache-quantization \
  --kv-cache-quantization-bits 8 \
  --cache-memory-mb "${CACHE_MEMORY_MB:-4096}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION:-0.95}" \
  --stream-interval "${STREAM_INTERVAL:-1}" \
  --max-tokens "${MAX_TOKENS:-8192}" \
  --default-temperature 0.3 \
  --no-thinking \
  --no-gc-control
