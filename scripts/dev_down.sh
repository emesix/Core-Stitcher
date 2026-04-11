#!/usr/bin/env bash
# Stop Stitch backend + lite UI.
for pidfile in /tmp/stitch-backend.pid /tmp/stitch-lite.pid; do
    if [ -f "$pidfile" ]; then
        PID=$(cat "$pidfile")
        if kill "$PID" 2>/dev/null; then
            echo "Stopped $(basename "$pidfile" .pid) (PID $PID)"
        fi
        rm -f "$pidfile"
    fi
done
