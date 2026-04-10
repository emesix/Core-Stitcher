#!/usr/bin/env bash
# Pre-tool-use hook: Block destructive stitch MCP operations without explicit approval.
#
# This hook intercepts stitch_interface_assign calls with dry_run=false
# and blocks them unless the tool input contains explicit approval markers.
#
# Registered in settings.json as a PreToolUse hook for MCP tools.

set -euo pipefail

# Read the tool use event from stdin
INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')

# Only intercept stitch write-path tools
case "$TOOL_NAME" in
  stitch_interface_assign)
    DRY_RUN=$(echo "$INPUT" | jq -r '.tool_input.dry_run // "true"')
    if [ "$DRY_RUN" = "false" ]; then
      DEVICE=$(echo "$INPUT" | jq -r '.tool_input.device_id // "unknown"')
      IFACE=$(echo "$INPUT" | jq -r '.tool_input.physical_interface // "unknown"')
      ROLE=$(echo "$INPUT" | jq -r '.tool_input.assign_as // "unknown"')
      echo "BLOCK: stitch_interface_assign with dry_run=false requires explicit confirmation."
      echo "Target: ${DEVICE}/${IFACE} -> ${ROLE}"
      echo "Re-run with dry_run=true first to preview, then confirm the exact change."
      exit 1
    fi
    ;;
  # Future write-path tools would be added here:
  # stitch_vlan_apply|stitch_config_push)
  #   ...
  #   ;;
esac

# Allow all other tools
exit 0
