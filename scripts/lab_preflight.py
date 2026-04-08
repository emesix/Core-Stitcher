"""Lab preflight smoke test — runs the full pipeline against real hardware.

Usage:
    uv run python scripts/lab_preflight.py
    uv run python scripts/lab_preflight.py --health-only
    uv run python scripts/lab_preflight.py --output output/run1

Requires MCP gateway running at localhost:4444 with switchcraft, opnsense,
and proxmox servers connected.

KNOWN ISSUES (2026-04-08):
    - Switchcraft IPs are stale for some devices (onti-backend/frontend swapped,
      zyxel at .3 instead of .33, 91tsm at .6 instead of .32). These need to be
      fixed in the switchcraft config before live collection will work correctly.
    - ONTi-BE ports 7/8: SFP modules not installed. Expect LINK_DOWN for
      backend paths to HX310-DB and HX310-ARR.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from vos.collectkit.merger import merge_observations
from vos.graphkit.diagnostics import diagnostics
from vos.modelkit.enums import PortType
from vos.opnsensecraft.collector import OpnsensecraftCollector
from vos.proxmoxcraft.collector import ProxmoxcraftCollector
from vos.storekit import load_topology
from vos.switchcraft.collector import SwitchcraftCollector
from vos.verifykit.engine import verify_topology

TOPOLOGY_PATH = Path(__file__).parent.parent / "topologies" / "lab.json"

# MCP device IDs from switchcraft-list-devices (2026-04-08)
# NOTE: IPs in switchcraft config are stale — names map to wrong hosts.
# The device IDs are what matter for the MCP gateway routing.
SWITCH_COLLECTORS = [
    SwitchcraftCollector(
        device_slug="onti-fe",
        mcp_device_id="onti-frontend",
        device_name="ONTi-FE (Frontend)",
        device_type="switch",
        port_type=PortType.SFP_PLUS,
    ),
    SwitchcraftCollector(
        device_slug="onti-be",
        mcp_device_id="onti-backend",
        device_name="ONTi-BE (Backend)",
        device_type="switch",
        port_type=PortType.SFP_PLUS,
    ),
    SwitchcraftCollector(
        device_slug="91tsm",
        mcp_device_id="91tsm",
        device_name="91TSM (Copper Breakout)",
        device_type="switch",
        port_type=PortType.ETHERNET,
    ),
    SwitchcraftCollector(
        device_slug="zyxel-gs1900",
        mcp_device_id="zyxel-frontend",
        device_name="Zyxel GS1900-24HP",
        device_type="switch",
        port_type=PortType.ETHERNET,
    ),
]

OPNSENSE_COLLECTOR = OpnsensecraftCollector(
    device_slug="opnsense",
    device_name="OPNsense",
    management_ip="192.168.254.1",
)

PROXMOX_COLLECTORS = [
    ProxmoxcraftCollector(
        device_slug="pve-qotom-1u",
        node_name="pve-qotom-1u",
        device_name="Qotom (Proxmox Host)",
        management_ip="192.168.254.100",
    ),
    ProxmoxcraftCollector(
        device_slug="pve-hx310-db",
        node_name="pve-hx310-db",
        device_name="HX310-DB (Database Node)",
        management_ip="192.168.254.101",
    ),
    ProxmoxcraftCollector(
        device_slug="pve-hx310-arr",
        node_name="pve-hx310-arr",
        device_name="HX310-ARR (ARR Services Node)",
        management_ip="192.168.254.102",
    ),
]

ALL_COLLECTORS = [*SWITCH_COLLECTORS, OPNSENSE_COLLECTOR, *PROXMOX_COLLECTORS]


def _dump_json(data: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        serializable = data.model_dump(mode="json")  # type: ignore[union-attr]
    elif isinstance(data, list):
        serializable = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in data
        ]
    else:
        serializable = data
    path.write_text(json.dumps(serializable, indent=2, default=str) + "\n")
    print(f"  -> {path}")


async def run_health_check() -> dict[str, object]:
    """Check reachability of all devices via MCP gateway."""
    print("=== HEALTH CHECK ===\n")
    results: dict[str, object] = {}

    for collector in ALL_COLLECTORS:
        slug = collector._device_slug
        try:
            health = await collector.check_health()
            status = health.get("status", "unknown")
            icon = {"ok": "+", "degraded": "~", "error": "!"}
            print(f"  [{icon.get(status, '?')}] {slug}: {status}")
            if health.get("message"):
                print(f"      {health['message']}")
            results[slug] = health
        except Exception as e:
            print(f"  [!] {slug}: EXCEPTION - {e}")
            results[slug] = {"status": "error", "message": str(e)}

    print()
    return results


async def run_preflight(output_dir: Path) -> None:
    """Full preflight: collect -> merge -> verify -> report."""
    print(f"=== PREFLIGHT RUN ({datetime.now(UTC).isoformat()}) ===\n")

    # 1. Load declared topology
    print("Loading declared topology...")
    declared = load_topology(TOPOLOGY_PATH)
    print(f"  Devices: {len(declared.devices)}, Links: {len(declared.links)}, "
          f"VLANs: {len(declared.vlans)}\n")

    # 2. Collect from all adapters (concurrent)
    print("Collecting from live devices...")
    all_observations = []
    errors: dict[str, str] = {}

    async def _collect_one(collector: object) -> None:
        slug = collector._device_slug  # type: ignore[attr-defined]
        try:
            obs = await collector.collect()  # type: ignore[attr-defined]
            print(f"  [{len(obs):3d} obs] {slug}")
            all_observations.extend(obs)
        except Exception as e:
            print(f"  [FAIL ] {slug}: {e}")
            errors[slug] = str(e)

    await asyncio.gather(*[_collect_one(c) for c in ALL_COLLECTORS])
    print(f"\n  Total observations: {len(all_observations)}")
    if errors:
        print(f"  Failed collectors: {list(errors.keys())}")
    print()

    # Save raw observations
    _dump_json(all_observations, output_dir / "raw_observations.json")

    # 3. Merge observations
    print("Merging observations...")
    observed, conflicts = merge_observations(all_observations)
    print(f"  Merged devices: {len(observed.devices)}")
    print(f"  Merge conflicts: {len(conflicts)}")
    if conflicts:
        for c in conflicts[:5]:
            print(f"    - {c.device}.{c.port}.{c.field}: {c.values}")
    print()

    _dump_json(observed, output_dir / "merged_snapshot.json")
    _dump_json(conflicts, output_dir / "merge_conflicts.json")

    # 4. Verify declared vs observed
    print("Verifying topology...")
    report = verify_topology(declared, observed)
    print(f"  Total checks: {len(report.results)}")

    # Count by severity
    severities: dict[str, int] = {}
    for r in report.results:
        sev = r.highest_severity if hasattr(r, "highest_severity") else "unknown"
        severities[sev] = severities.get(sev, 0) + 1
    for sev, count in sorted(severities.items()):
        print(f"    {sev}: {count}")
    print()

    _dump_json(report, output_dir / "verification_report.json")

    # 5. Diagnostics
    print("Running diagnostics...")
    diag = diagnostics(declared)
    print(f"  Dangling ports: {len(diag.dangling_ports)}")
    print(f"  Orphan devices: {len(diag.orphan_devices)}")
    print(f"  Missing endpoints: {len(diag.missing_endpoints)}")
    print()

    _dump_json(diag, output_dir / "diagnostics.json")

    # 6. Summary
    _dump_json(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "topology": declared.meta.name,
            "devices_declared": len(declared.devices),
            "observations_collected": len(all_observations),
            "devices_observed": len(observed.devices),
            "merge_conflicts": len(conflicts),
            "verification_checks": len(report.results),
            "collection_errors": errors,
        },
        output_dir / "summary.json",
    )

    print(f"=== DONE — artifacts in {output_dir}/ ===")


def main() -> None:
    parser = argparse.ArgumentParser(description="Core-Stitcher lab preflight")
    parser.add_argument("--health-only", action="store_true", help="Only run health checks")
    parser.add_argument("--output", type=Path, default=Path("output/latest"),
                        help="Output directory for artifacts")
    args = parser.parse_args()

    if args.health_only:
        asyncio.run(run_health_check())
    else:
        asyncio.run(run_preflight(args.output))


if __name__ == "__main__":
    main()
