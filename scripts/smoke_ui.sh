#!/usr/bin/env bash
# Verify all UI pages return 200 with real data. Run after dev_up.sh.
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

pass() { echo -e "${GREEN}PASS${NC} $1"; }
fail() { echo -e "${RED}FAIL${NC} $1"; FAILURES=$((FAILURES + 1)); }

BACKEND="${STITCH_BACKEND:-http://localhost:8000}"
LITE="${STITCH_LITE:-http://localhost:8080}"
FAILURES=0

echo "=== UI Smoke Test ==="

# Backend API
echo "--- Backend ---"
curl -s -f "$BACKEND/api/v1/health/modules" > /dev/null 2>&1 && pass "Health endpoint" || fail "Health endpoint"
curl -s -f "$BACKEND/api/v1/explorer/devices" > /dev/null 2>&1 && pass "Devices API" || fail "Devices API"
curl -s -f "$BACKEND/api/v1/explorer/topology" > /dev/null 2>&1 && pass "Topology API" || fail "Topology API"

# Lite pages
echo "--- Lite UI ---"
for path in / /devices /topology /runs /preflight /opnsense /system; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$LITE$path" 2>/dev/null)
    if [ "$STATUS" = "200" ]; then
        pass "GET $path"
    else
        fail "GET $path (HTTP $STATUS)"
    fi
done

# Real data in pages
echo "--- Real data ---"
curl -s "$LITE/devices" 2>/dev/null | grep -q "opnsense" && pass "Device: opnsense visible" || fail "Device: opnsense not found"
curl -s "$LITE/topology" 2>/dev/null | grep -qi "emesix\|lab" && pass "Topology: name visible" || fail "Topology: name not found"

# OPNsense
echo "--- OPNsense ---"
curl -s -f "$BACKEND/api/v1/opnsense/summary" > /dev/null 2>&1 && pass "Backend: OPNsense summary API" || fail "Backend: OPNsense summary API"
curl -s "$LITE/opnsense" 2>/dev/null | grep -qi "interfaces\|working\|error" && pass "OPNsense: service cards visible" || fail "OPNsense: no service data"

echo ""
if [ "$FAILURES" -eq 0 ]; then
    echo -e "${GREEN}All checks passed.${NC}"
else
    echo -e "${RED}${FAILURES} check(s) failed.${NC}"
    exit 1
fi
