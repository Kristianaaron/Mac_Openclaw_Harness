# OpenClaw Obsidian Wiki Maintenance Layer

## Overview

This template provides a wiki maintenance layer for your knowledge base using Karpathy's LLM Wiki pattern. It integrates with Obsidian and runs via OpenClaw.

## Components

### 1. Vault Structure (`~/Documents/Knowledge/`)

```
Knowledge/
├── AGENTS.md     # Schema - SINGLE SOURCE OF TRUTH (required for ALL agents)
├── index.md      # Map of all wiki pages
├── log.md        # Change history
├── inbox/        # Raw sources
└── wiki/         # Compiled articles
```

### 2. Lint Skill (`obsidian-wiki-lint`)

Health check that runs on the wiki:
- Detects contradictions
- Finds orphan pages
- Identifies gaps
- Flags stale information

## Setup

### Option 1: Use Template as-is

Copy `skills/` to OpenClaw skills:
```bash
cp -r skills/obsidian-wiki-lint ~/.openclaw/skills/
```

### Option 2: Clone for New Machine
```bash
git clone https://github.com/Kristianaaron/Mac_Openclaw_Harness.git
cp -r Mac_Openclaw_Harness/wiki-maintenance/skills/obsidian-wiki-lint ~/.openclaw/skills/
```

## Usage

### Manual Lint
```bash
~/.openclaw/skills/obsidian-wiki-lint/main.zsh
```

### Via Cron (Weekly)
```bash
# Add to crontab
0 9 * * SAT ~/.openclaw/skills/obsidian-wiki-lint/main.zsh >> ~/Documents/Knowledge/lint-cron.log 2>&1
```

## AGENTS.md Schema

The vault's `AGENTS.md` is the **single source of truth** for ALL agents:
- Must be read before any operation
- Contains guardrails and conventions
- Mitigation: validates schema exists before lint runs
- Logs schema hash for audit trail

## Vault Location

Default: `~/Documents/Knowledge/`

Change in `skill.yaml`:
```yaml
vault_path: /custom/path
```

## GitHub Sync

Manual push when you want a checkpoint:
```bash
cd ~/Documents/Knowledge
git add -A
git commit -m "Wiki update: $(date)"
git push origin main
```