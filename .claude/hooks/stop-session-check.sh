#!/usr/bin/env bash
# Stop hook: Remind about pending changes before session ends.
#
# Checks if any real (non-dry-run) interface assignments were made
# during this session and reminds to summarize changes.

set -euo pipefail

AUDIT_FILE="$HOME/.stitch/audit.jsonl"

if [ -f "$AUDIT_FILE" ]; then
  # Count real applies in the last hour (approximate session window)
  RECENT_APPLIES=$(awk -v cutoff="$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '$0 ~ /"applied":"true"/ || $0 ~ /"applied":true/' "$AUDIT_FILE" | wc -l)

  if [ "$RECENT_APPLIES" -gt 0 ]; then
    echo "NOTE: $RECENT_APPLIES infrastructure change(s) were applied this session."
    echo "Before ending, please summarize: what changed, verification status, and rollback steps."
  fi
fi

exit 0
