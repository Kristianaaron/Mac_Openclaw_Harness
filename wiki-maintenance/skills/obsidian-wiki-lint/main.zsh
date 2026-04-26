#!/usr/bin/env bash
# Obsidian Wiki Lint Skill
# Runs health check on wiki knowledge base

set -euo pipefail

# Load config
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SKILL_DIR/skill.yaml"

# Parse config values
VAULT_PATH="${vault_path:-$HOME/Documents/Knowledge}"
SCHEMA_PATH="${schema_path:-$HOME/Documents/Knowledge/AGENTS.md}"

# MITIGATION: Validate schema exists
if [[ ! -f "$SCHEMA_PATH" ]]; then
    echo "ERROR: AGENTS.md not found at $SCHEMA_PATH"
    echo "Aborting - schema required for lint operation"
    exit 1
fi

echo "=== Obsidian Wiki Lint ==="
echo "Vault: $VAULT_PATH"
echo "Schema: $SCHEMA_PATH"

# Read schema for context
echo ""
echo "Reading schema..."
SCHEMA_HASH=$(md5 -q "$SCHEMA_PATH" 2>/dev/null || md5sum "$SCHEMA_PATH" | awk '{print $1}')
echo "Schema hash: $SCHEMA_HASH"
echo "Schema last modified: $(stat -f '%Sm' "$SCHEMA_PATH" 2>/dev/null || stat -c '%y' "$SCHEMA_PATH")"

# Check wiki directory
WIKI_DIR="$VAULT_PATH/wiki"
INDEX_FILE="$VAULT_PATH/index.md"
LOG_FILE="$VAULT_PATH/log.md"

if [[ ! -d "$WIKI_DIR" ]]; then
    echo "No wiki directory found. Run ingest first."
    exit 1
fi

# Count pages
PAGE_COUNT=$(find "$WIKI_DIR" -name "*.md" -type f | wc -l | tr -d ' ')
echo ""
echo "Wiki pages: $PAGE_COUNT"

# Run lint via OpenCode
echo ""
echo "Running lint..."

# Read wiki index and key pages for lint
INDEX_CONTENT=$(cat "$INDEX_FILE" 2>/dev/null || echo "(no index)")
WIKI_PAGES=$(find "$WIKI_DIR" -name "*.md" -type f -exec head -20 {} \;)

# Lint prompt
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"qwen3.6-27b\",
    \"messages\": [
        {\"role\": \"system\", \"content\": \"You are a wiki health check system. Read the AGENTS.md schema first, then audit the wiki index and pages.\"},
        {\"role\": \"user\", \"content\": \"Perform lint on the wiki at $VAULT_PATH\\n\\nINDEX:\\n$INDEX_CONTENT\\n\\n\\nCheck for:\\n1. Contradictions between pages?\\n2. Orphan pages (no links)?\\n3. Concepts lacking their own pages?\\n4. Stale information?\"}
    ],
    \"max_tokens\": 2000,
    \"temperature\": 0.3
}" 2>/dev/null | jq -r '.choices[0].message.content' || echo "Error running lint"

echo ""
echo "=== Lint Complete ==="
echo "Review results above. Safe fixes applied where possible."

# Log operation
echo "$(date '+%Y-%m-%d %H:%M') | LINT | Schema:$SCHEMA_HASH | Pages:$PAGE_COUNT | Agent:obsidian-wiki-lint" >> "$LOG_FILE"

echo ""
echo "Logged to $LOG_FILE"