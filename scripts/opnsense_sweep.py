"""Automated OPNsense capability sweep via MCP gateway.

Probes each safe-read / sensitive-read tool sequentially (OPNsense rate-limit
safety: never parallel, 0.5s delay between calls) and produces:
  - output/opnsense-capabilities.json  (machine-readable)
  - docs/ops/opnsense-api-validation-YYYY-MM-DD.md  (human-readable)
"""

from __future__ import annotations

import asyncio
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from stitch.apps.backend.opnsense_models import (
    CapabilitySweepResult,
    ProbeStatus,
    ToolClassification,
    ToolProbeResult,
)
from stitch.contractkit.gateway import McpGatewayClient

# ── Tool catalogue ──────────────────────────────────────────────────

TOOL_CATALOGUE: list[dict[str, str]] = [
    {"tool": "opnsense-get-interfaces", "category": "interfaces", "cls": "safe_read"},
    {"tool": "opnsense-get-system-status", "category": "system", "cls": "safe_read"},
    {"tool": "opnsense-get-system-health", "category": "system_health", "cls": "safe_read"},
    {"tool": "opnsense-get-system-routes", "category": "routes", "cls": "safe_read"},
    {"tool": "opnsense-firewall-get-rules", "category": "firewall_rules", "cls": "safe_read"},
    {"tool": "opnsense-get-firewall-aliases", "category": "firewall_aliases", "cls": "safe_read"},
    {"tool": "opnsense-nat-get-port-forward-info", "category": "nat", "cls": "safe_read"},
    {"tool": "opnsense-dhcp-list-servers", "category": "dhcp_servers", "cls": "safe_read"},
    {"tool": "opnsense-dhcp-get-leases", "category": "dhcp_leases", "cls": "safe_read"},
    {"tool": "opnsense-dhcp-list-static-mappings", "category": "dhcp_static", "cls": "safe_read"},
    {"tool": "opnsense-dns-resolver-get-settings", "category": "dns_settings", "cls": "safe_read"},
    {
        "tool": "opnsense-dns-resolver-list-host-overrides",
        "category": "dns_overrides",
        "cls": "safe_read",
    },
    {"tool": "opnsense-get-vpn-connections", "category": "vpn", "cls": "safe_read"},
    {"tool": "opnsense-list-certificates", "category": "certificates", "cls": "sensitive_read"},
    {"tool": "opnsense-list-users", "category": "users", "cls": "sensitive_read"},
    {"tool": "opnsense-list-plugins", "category": "plugins", "cls": "safe_read"},
    {"tool": "opnsense-backup-config", "category": "config_backup", "cls": "sensitive_read"},
    {"tool": "opnsense-list-vlan-interfaces", "category": "vlans", "cls": "safe_read"},
    {"tool": "opnsense-list-bridge-interfaces", "category": "bridges", "cls": "safe_read"},
]

INTER_CALL_DELAY = 0.5  # seconds between gateway calls (OPNsense rate-limit safety)
PER_TOOL_TIMEOUT = 15.0  # generous timeout per tool
GATEWAY_TARGET = "172.16.0.1"  # OPNsense appliance address (informational)


# ── Probe logic ─────────────────────────────────────────────────────


def _count_items(data: object) -> int | None:
    """Best-effort item count from raw gateway response."""
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        # Many OPNsense tools return {"rows": [...]} or {"items": [...]}
        for key in ("rows", "items", "leases", "rules", "interfaces", "entries"):
            if key in data and isinstance(data[key], list):
                return len(data[key])
        # If all values are dicts, treat top-level keys as items (e.g. interfaces)
        if data and all(isinstance(v, dict) for v in data.values()):
            return len(data)
    return None


def _classify_error(exc: Exception) -> tuple[ProbeStatus, str, str]:
    """Map exception to (status, error_code, error_message)."""
    msg = str(exc)
    if "timeout" in msg.lower() or isinstance(exc, asyncio.TimeoutError):
        return ProbeStatus.TIMEOUT, "timeout", msg
    if "401" in msg or "403" in msg:
        return ProbeStatus.AUTH_ERROR, "auth", msg
    if "404" in msg:
        return ProbeStatus.NOT_FOUND, "not_found", msg
    return ProbeStatus.ERROR, type(exc).__name__, msg


async def probe_tool(
    gw: McpGatewayClient,
    tool: str,
    category: str,
    classification: ToolClassification,
) -> ToolProbeResult:
    """Probe a single tool and return the result."""
    t0 = time.monotonic()
    try:
        result = await gw.call_tool(tool, timeout=PER_TOOL_TIMEOUT)
        latency = (time.monotonic() - t0) * 1000

        if result is None:
            return ToolProbeResult(
                tool=tool,
                category=category,
                classification=classification,
                status=ProbeStatus.EMPTY,
                latency_ms=round(latency, 1),
                error_message="gateway returned None (empty content or RPC error)",
            )

        item_count = _count_items(result)
        status = ProbeStatus.EMPTY if item_count == 0 else ProbeStatus.WORKS

        return ToolProbeResult(
            tool=tool,
            category=category,
            classification=classification,
            status=status,
            latency_ms=round(latency, 1),
            item_count=item_count,
        )

    except Exception as exc:
        latency = (time.monotonic() - t0) * 1000
        status, code, msg = _classify_error(exc)
        return ToolProbeResult(
            tool=tool,
            category=category,
            classification=classification,
            status=status,
            latency_ms=round(latency, 1),
            error_code=code,
            error_message=msg,
        )


# ── Sweep runner ────────────────────────────────────────────────────


async def run_sweep() -> CapabilitySweepResult:
    gw = McpGatewayClient()
    results: list[ToolProbeResult] = []

    print(f"Starting OPNsense capability sweep ({len(TOOL_CATALOGUE)} tools)...")
    print(f"Gateway: {gw._gateway_url}/mcp/")
    print(f"Target:  {GATEWAY_TARGET}")
    print()

    try:
        for i, entry in enumerate(TOOL_CATALOGUE):
            if i > 0:
                await asyncio.sleep(INTER_CALL_DELAY)

            cls = ToolClassification(entry["cls"])
            tag = f"[{i + 1}/{len(TOOL_CATALOGUE)}]"
            print(f"  {tag} {entry['tool']} ({entry['category']})...", end=" ", flush=True)

            result = await probe_tool(gw, entry["tool"], entry["category"], cls)
            results.append(result)

            if result.status == ProbeStatus.WORKS:
                print(f"OK ({result.item_count} items, {result.latency_ms:.0f}ms)")
            elif result.status == ProbeStatus.EMPTY:
                print(f"EMPTY ({result.latency_ms:.0f}ms)")
            else:
                print(f"{result.status.value.upper()} — {result.error_message or '?'}")
    finally:
        await gw.close()

    summary = dict(Counter(r.status.value for r in results))

    return CapabilitySweepResult(
        timestamp=datetime.now(UTC),
        target=GATEWAY_TARGET,
        results=results,
        summary=summary,
    )


# ── Output writers ──────────────────────────────────────────────────


def write_json(sweep: CapabilitySweepResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(sweep.model_dump_json(indent=2) + "\n")
    print(f"\nJSON written to {path}")


def write_markdown(sweep: CapabilitySweepResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    status_emoji = {
        "works": "OK",
        "empty": "EMPTY",
        "auth_error": "AUTH",
        "not_found": "404",
        "error": "ERR",
        "timeout": "TIMEOUT",
        "skipped": "SKIP",
    }

    lines = [
        f"# OPNsense API Validation — {sweep.timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"**Target:** {sweep.target}",
        f"**Tools probed:** {len(sweep.results)}",
        "",
        "## Summary",
        "",
    ]
    for status, count in sorted(sweep.summary.items()):
        lines.append(f"- **{status}**: {count}")
    lines.append("")

    lines.append("## Results")
    lines.append("")
    lines.append("| # | Tool | Category | Class | Status | Items | Latency |")
    lines.append("|---|------|----------|-------|--------|-------|---------|")
    for i, r in enumerate(sweep.results, 1):
        tag = status_emoji.get(r.status.value, r.status.value)
        items = str(r.item_count) if r.item_count is not None else "—"
        latency = f"{r.latency_ms:.0f}ms" if r.latency_ms is not None else "—"
        cls_val = r.classification.value
        row = f"| {i} | `{r.tool}` | {r.category} | {cls_val} | {tag} | {items} | {latency} |"
        lines.append(row)

    # Errors section
    errors = [r for r in sweep.results if r.error_message]
    if errors:
        lines.append("")
        lines.append("## Errors")
        lines.append("")
        for r in errors:
            lines.append(f"- **{r.tool}**: {r.error_message}")

    lines.append("")
    path.write_text("\n".join(lines))
    print(f"Report written to {path}")


# ── Main ────────────────────────────────────────────────────────────


async def main() -> None:
    sweep = await run_sweep()

    repo_root = Path(__file__).resolve().parent.parent
    today = datetime.now(UTC).strftime("%Y-%m-%d")

    write_json(sweep, repo_root / "output" / "opnsense-capabilities.json")
    write_markdown(sweep, repo_root / "docs" / "ops" / f"opnsense-api-validation-{today}.md")

    # Print summary
    print(f"\nSweep complete: {sweep.summary}")

    # Also dump JSON to stdout for piping
    print("\n--- JSON ---")
    print(sweep.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
