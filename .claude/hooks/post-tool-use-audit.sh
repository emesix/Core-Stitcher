#!/usr/bin/env bash
# Post-tool-use hook: Audit log all stitch MCP write operations.
#
# Appends a normalized JSON record to ~/.stitch/audit.jsonl after every
# write-path tool call, regardless of success or failure.

set -euo pipefail

INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')

# Only audit stitch write-path tools
case "$TOOL_NAME" in
  stitch_interface_assign)
    AUDIT_DIR="$HOME/.stitch"
    AUDIT_FILE="$AUDIT_DIR/audit.jsonl"
    mkdir -p "$AUDIT_DIR"

    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    TOOL_INPUT=$(echo "$INPUT" | jq -c '.tool_input // {}')
    TOOL_OUTPUT=$(echo "$INPUT" | jq -c '.tool_output // {}')

    # Extract key fields from output
    OK=$(echo "$TOOL_OUTPUT" | jq -r '.ok // "unknown"')
    APPLIED=$(echo "$TOOL_OUTPUT" | jq -r '.result.applied // false')

    jq -n --arg ts "$TIMESTAMP" \
           --arg tool "$TOOL_NAME" \
           --argjson input "$TOOL_INPUT" \
           --arg ok "$OK" \
           --arg applied "$APPLIED" \
           '{"timestamp":$ts,"tool":$tool,"input":$input,"ok":$ok,"applied":$applied}' \
      >> "$AUDIT_FILE"
    ;;
esac

exit 0
