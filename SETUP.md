# OpenClaw Gemma JANQ TUI Harness Setup

This repository installs the Mac-side OpenClaw TUI harness for the current local
Gemma 4 JANQ runtime. It replaces the older Qwen port-8000 setup with the same
profile-driven model server used by the newer OpenClaw autoresearch harness.

## Current Target

- OpenClaw CLI: `/opt/homebrew/bin/openclaw`
- Gateway: `http://127.0.0.1:18789`
- Model provider: `mlx`
- Model ref: `mlx/Gemma-4-31B-JANG_4M-CRACK`
- OpenAI-compatible model API: `http://127.0.0.1:8091/v1`
- Upstream JANG/VLM server: `127.0.0.1:8086`
- Model profile file: `~/.openclaw/model-profiles.json`

## Install

```bash
cd /Users/kristian/Documents/Mac_Openclaw_Harness
./scripts/install-openclaw-harness.sh
```

The installer backs up existing wrapper/profile/sidecar targets before copying:

- `openclaw-local-wrapper.zsh` -> `~/.zfunc/openclaw-tui-harness` if an
  existing `~/.zfunc/openclaw` is present
- `scripts/openclaw-tui-self-improvement.py` -> `~/.openclaw/bin/openclaw-tui-self-improvement`
- `config/model-profiles.json` -> `~/.openclaw/model-profiles.json`

If `~/.openclaw/openclaw.json` already exists, the installer keeps it and asks
the model-profile helper to sync the active model/provider fields. It only
copies `openclaw-local-mlx-config.json` when no OpenClaw config exists yet.

To intentionally replace the active `openclaw` wrapper after review:

```bash
OPENCLAW_INSTALL_REPLACE_WRAPPER=1 ./scripts/install-openclaw-harness.sh
```

## Verify

```bash
./scripts/verify-harness.sh
openclaw doctor
openclaw model-status
```

## Use

```bash
openclaw tui
```

The wrapper resolves the active model profile, starts the matching LaunchAgent
only if needed, applies the memory gate before launching the 31B model, warms the
prefix cache, starts the OpenClaw gateway, and runs a lightweight TUI
self-improvement health snapshot in the background.

## Self-Improvement Sidecar

```bash
openclaw doctor
openclaw self-improve --json
```

The sidecar checks:

- active model/profile drift
- gateway and model API reachability
- memory pressure
- recent logs for crash, timeout, repeated reasoning, and malformed tool-call markers

It writes reports to `~/.openclaw/tui-self-improvement/reports/` and a durable
journal to `~/.openclaw/tui-self-improvement/journal.jsonl`. It is
observational by default and does not mutate the model, provider, runtime, or
OpenClaw source.

## Safety Notes

- This repo is OpenClaw-only. It does not configure opencode.
- No tokens, API keys, or environment files are required.
- `local-dev-token` and `custom-local` are local placeholders, not external secrets.
- The wrapper refuses to start another large local model when macOS memory
  pressure is already unsafe.
