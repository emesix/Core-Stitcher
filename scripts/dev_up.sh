#!/usr/bin/env bash
# Start Stitch backend + lite UI. One command to working product.
set -euo pipefail

BACKEND_PORT="${STITCH_BACKEND_PORT:-8000}"
LITE_PORT="${STITCH_LITE_PORT:-8080}"
TOPO="${STITCH_TOPOLOGY:-topologies/lab.json}"

echo "Starting Stitch backend on :${BACKEND_PORT}..."
uv run stitch-server --topology "$TOPO" --port "$BACKEND_PORT" &
BACKEND_PID=$!
echo "$BACKEND_PID" > /tmp/stitch-backend.pid

sleep 3

if ! curl -s -f "http://localhost:${BACKEND_PORT}/api/v1/health/modules" > /dev/null 2>&1; then
    echo "ERROR: Backend failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo "Starting Stitch Lite on :${LITE_PORT}..."
STITCH_SERVER="http://localhost:${BACKEND_PORT}" uv run stitch-lite --port "$LITE_PORT" &
LITE_PID=$!
echo "$LITE_PID" > /tmp/stitch-lite.pid

sleep 2

if ! curl -s -f "http://localhost:${LITE_PORT}/" > /dev/null 2>&1; then
    echo "ERROR: Lite failed to start"
    kill $BACKEND_PID $LITE_PID 2>/dev/null
    exit 1
fi

echo ""
echo "Stitch is running:"
echo "  Backend API:  http://localhost:${BACKEND_PORT}"
echo "  Stitch Lite:  http://localhost:${LITE_PORT}"
echo ""
echo "Stop with: ./scripts/dev_down.sh"
