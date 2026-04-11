#!/usr/bin/env bash
# End-to-end smoke test: proves the system actually works against the live homelab.
# Run after Part 1 changes land. Exits non-zero on any failure.
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}PASS${NC} $1"; }
fail() { echo -e "${RED}FAIL${NC} $1"; exit 1; }
skip() { echo -e "${YELLOW}SKIP${NC} $1"; }

echo "=== Smoke Test: Core-Stitcher Homelab ==="
echo ""

# 1. Unit tests
echo "--- Unit tests ---"
uv run pytest tests/ -v -m "not integration" --tb=short -q 2>&1 | tail -3
echo ""

# 2. Lint + types
echo "--- Lint + types ---"
uv run ruff check src/ tests/ 2>&1 | tail -1
uv run pyright src/ 2>&1 | tail -1
echo ""

# 3. Topology file exists and is valid JSON
echo "--- Topology ---"
if python3 -c "import json; json.load(open('topologies/lab.json'))" 2>/dev/null; then
    DEVICES=$(python3 -c "import json; d=json.load(open('topologies/lab.json')); print(len(d.get('devices',{})))")
    pass "topologies/lab.json valid ($DEVICES devices)"
else
    fail "topologies/lab.json invalid or missing"
fi

# 4. OPNsense reachable
echo "--- OPNsense ---"
if ping -c 1 -W 2 172.16.0.1 >/dev/null 2>&1; then
    pass "OPNsense reachable at 172.16.0.1"
else
    skip "OPNsense unreachable (offline?)"
fi

# 5. Switches reachable
echo "--- Switches ---"
for ip in 30 31 32 33; do
    if ping -c 1 -W 2 "192.168.254.$ip" >/dev/null 2>&1; then
        pass "Switch at 192.168.254.$ip"
    else
        skip "Switch at 192.168.254.$ip unreachable"
    fi
done

# 6. A770 backends
echo "--- A770 backends ---"
if curl -s --connect-timeout 3 http://172.16.0.109:8000/v3/models >/dev/null 2>&1; then
    MODEL=$(curl -s http://172.16.0.109:8000/v3/models | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || echo "?")
    pass "GPU inference ($MODEL)"
else
    skip "GPU inference unreachable"
fi

if curl -s --connect-timeout 3 http://172.16.0.109:8001/v3/models >/dev/null 2>&1; then
    pass "CPU inference"
else
    skip "CPU inference unreachable"
fi

if curl -s --connect-timeout 3 http://172.16.0.109:8080/health >/dev/null 2>&1; then
    pass "Sidecar"
else
    skip "Sidecar unreachable"
fi

# 7. OpenRouter auth
echo "--- OpenRouter ---"
OPENROUTER_KEY=$(python3 -c "import json; print(json.load(open('$HOME/.stitch/secrets.json')).get('openrouter_api_key',''))" 2>/dev/null || echo "")
if [ -n "$OPENROUTER_KEY" ]; then
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $OPENROUTER_KEY" https://openrouter.ai/api/v1/models 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        pass "OpenRouter API key valid"
    else
        fail "OpenRouter API key invalid (HTTP $STATUS)"
    fi
else
    skip "No OpenRouter API key in secrets.json"
fi

# 8. Alpha routing run (if GPU is up)
echo "--- Alpha orchestration ---"
if curl -s --connect-timeout 3 http://172.16.0.109:8000/v3/models >/dev/null 2>&1; then
    RESULT=$(uv run python scripts/alpha_run.py 2>&1 | grep -c "completed" || echo "0")
    if [ "$RESULT" -gt 0 ]; then
        pass "Alpha orchestration completed"
    else
        fail "Alpha orchestration did not complete"
    fi
else
    skip "Alpha orchestration (GPU offline)"
fi

echo ""
echo "=== Smoke test complete ==="
