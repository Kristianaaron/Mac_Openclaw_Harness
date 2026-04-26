# OpenClaw Qwen3.6-27B Setup

## Current Status
- MLX Server: Running on port 8000 with rapid-mlx
- OpenClaw Gateway: Running on port 18789
- Model: mlx-community/Qwen3.6-27B-4bit

## Throughput
- Direct MLX: 19 tok/s single, 25-44 tok/s with batching
- Through OpenClaw: ~4 tok/s (includes tool calling, streaming overhead)
- First-token latency: ~12s (model prefill time)

## Key Files
- MLX Config: `~/.openclaw/openclaw.json`
- Server Script: `run-qwen-rapid-mlx-server.sh`

## Optimizations Applied
1. Server batching: max-num-seqs=16, prefill-batch-size=16, completion-batch-size=32
2. KV cache quantization: 8-bit
3. Continuous batching enabled
4. contextWindow: 16384, maxTokens: 2048
5. Compaction: mode=default, maxHistoryShare=15%

## Issues Fixed
- Hallucinations: Fixed via temperature=0.3, maxTokens increased
- Session bloat: Configure memoryFlush and aggressive compaction
- Model ID mismatch: Changed from default_model to qwen3.6-27b

## To Start
```bash
cd ~/Documents/Codex/2026-04-25/hey-codex-are-you-able-to
./run-qwen-rapid-mlx-server.sh &
openclaw gateway run --port 18789 --token local-dev-token &
```

## For Fast Q&A (bypass OpenClaw overhead)
```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen3.6-27b", "messages": [{"role": "user", "content": "YOUR PROMPT"}], "max_tokens": 500}'
```

## Last Updated
2026-04-26