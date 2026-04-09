"""Core verification engine: declared vs observed → VerificationReport.

Pure evaluator. Two snapshots in, report out. Never loads files, never queries
DB, never calls adapters. The caller is responsible for providing the inputs.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

from stitch.modelkit.enums import CheckCategory, CheckSeverity, LinkType, ObservationSource
from stitch.modelkit.verification import CheckResult, LinkVerification, VerificationReport

if TYPE_CHECKING:
    from stitch.modelkit.link import Link
    from stitch.modelkit.port import Port
    from stitch.modelkit.topology import TopologySnapshot


# --- Category and severity mapping ---

_CHECK_CATEGORY: dict[tuple[str, str], CheckCategory] = {
    ("device_exists", "missing"): CheckCategory.ENDPOINT_MISSING,
    ("port_exists", "missing"): CheckCategory.ENDPOINT_MISSING,
    ("neighbor_match", "mismatch"): CheckCategory.NEIGHBOR_MISMATCH,
    ("vlan_compatibility", "mismatch"): CheckCategory.VLAN_MISMATCH,
    ("vlan_compatibility", "warning"): CheckCategory.VLAN_MISMATCH,
    ("bridge_membership", "missing"): CheckCategory.BRIDGE_MEMBERSHIP_MISMATCH,
    ("vlan_on_parent", "mismatch"): CheckCategory.VLAN_PARENT_MISMATCH,
}

_FLAG_SEVERITY: dict[str, CheckSeverity] = {
    "ok": CheckSeverity.INFO,
    "missing": CheckSeverity.ERROR,
    "mismatch": CheckSeverity.ERROR,
    "warning": CheckSeverity.WARNING,
}


def _classify(check: str, flag: str) -> tuple[CheckCategory | None, CheckSeverity]:
    """Return (category, severity) for a check result."""
    category = _CHECK_CATEGORY.get((check, flag))
    severity = _FLAG_SEVERITY.get(flag, CheckSeverity.INFO)
    return category, severity


# --- Public API ---


_SEVERITY_ORDER = {CheckSeverity.ERROR: 0, CheckSeverity.WARNING: 1, CheckSeverity.INFO: 2}
_STATUS_ORDER = {"fail": 0, "warning": 1, "pass": 2}


def verify_topology(
    declared: TopologySnapshot,
    observed: TopologySnapshot,
) -> VerificationReport:
    results: list[LinkVerification] = []

    for link in declared.links:
        checks = _verify_link(link, declared, observed)
        # Annotate each check with category and severity
        for c in checks:
            cat, sev = _classify(c.check, c.flag)
            c.category = cat
            c.severity = sev

        # Sort checks: errors first, then warnings, then info
        checks.sort(key=lambda c: _SEVERITY_ORDER.get(c.severity, 9))

        status = _link_status(checks)
        highest = _highest_severity(checks)
        results.append(
            LinkVerification(
                link=link.id,
                link_type=link.type,
                status=status,
                highest_severity=highest,
                checks=checks,
            )
        )

    # Sort results: fail first, then warning, then pass
    results.sort(key=lambda r: _STATUS_ORDER.get(r.status, 9))

    summary = _build_summary(results)
    return VerificationReport(results=results, summary=summary)


# --- Link verification (unchanged behavior) ---


def _verify_link(
    link: Link,
    declared: TopologySnapshot,
    observed: TopologySnapshot,
) -> list[CheckResult]:
    checks: list[CheckResult] = []
    ep_a, ep_b = link.endpoints

    for ep in (ep_a, ep_b):
        obs_dev = observed.devices.get(ep.device)
        if obs_dev is None:
            checks.append(
                CheckResult(
                    check="device_exists",
                    port=f"{ep.device}/{ep.port}",
                    expected=ep.device,
                    observed=None,
                    source=ObservationSource.DECLARED,
                    flag="missing",
                    message=f"Device '{ep.device}' not found in observed topology",
                )
            )
            continue

        obs_port = obs_dev.ports.get(ep.port)
        if obs_port is None:
            checks.append(
                CheckResult(
                    check="port_exists",
                    port=f"{ep.device}/{ep.port}",
                    expected=ep.port,
                    observed=None,
                    source=ObservationSource.DECLARED,
                    flag="missing",
                    message=f"Port '{ep.port}' not found on device '{ep.device}'",
                )
            )
            continue

        checks.append(
            CheckResult(
                check="port_exists",
                port=f"{ep.device}/{ep.port}",
                expected=ep.port,
                observed=ep.port,
                source=ObservationSource.MCP_LIVE,
                flag="ok",
            )
        )

    if link.type == LinkType.PHYSICAL_CABLE:
        checks.extend(_verify_physical_cable(link, declared, observed))
    elif link.type == LinkType.BRIDGE_MEMBER:
        checks.extend(_verify_bridge_member(link, declared, observed))
    elif link.type == LinkType.VLAN_PARENT:
        checks.extend(_verify_vlan_parent(link, declared, observed))

    return checks


def _verify_physical_cable(
    link: Link,
    declared: TopologySnapshot,
    observed: TopologySnapshot,
) -> list[CheckResult]:
    checks: list[CheckResult] = []
    ep_a, ep_b = link.endpoints

    port_a = _get_port(declared, ep_a.device, ep_a.port)
    port_b = _get_port(declared, ep_b.device, ep_b.port)

    if port_a is None or port_b is None:
        return checks

    if port_a.expected_neighbor is not None:
        if (
            port_a.expected_neighbor.device != ep_b.device
            or port_a.expected_neighbor.port != ep_b.port
        ):
            checks.append(
                CheckResult(
                    check="neighbor_match",
                    port=f"{ep_a.device}/{ep_a.port}",
                    expected=f"{port_a.expected_neighbor.device}/{port_a.expected_neighbor.port}",
                    observed=f"{ep_b.device}/{ep_b.port}",
                    source=ObservationSource.DECLARED,
                    flag="mismatch",
                    message="Expected neighbor does not match link endpoint",
                )
            )
        else:
            checks.append(
                CheckResult(
                    check="neighbor_match",
                    port=f"{ep_a.device}/{ep_a.port}",
                    expected=f"{ep_b.device}/{ep_b.port}",
                    observed=f"{ep_b.device}/{ep_b.port}",
                    source=ObservationSource.DECLARED,
                    flag="ok",
                )
            )

    checks.extend(_check_vlan_compatibility(port_a, port_b, ep_a, ep_b))

    return checks


def _verify_bridge_member(
    link: Link,
    declared: TopologySnapshot,
    observed: TopologySnapshot,
) -> list[CheckResult]:
    checks: list[CheckResult] = []
    ep_member, ep_bridge = link.endpoints

    bridge_port = _get_port(observed, ep_bridge.device, ep_bridge.port)
    member_port = _get_port(observed, ep_member.device, ep_member.port)

    if bridge_port is not None and member_port is not None:
        checks.append(
            CheckResult(
                check="bridge_membership",
                port=f"{ep_member.device}/{ep_member.port}",
                expected=f"member of {ep_bridge.port}",
                observed=f"member of {ep_bridge.port}",
                source=ObservationSource.MCP_LIVE,
                flag="ok",
            )
        )
    elif member_port is None:
        checks.append(
            CheckResult(
                check="bridge_membership",
                port=f"{ep_member.device}/{ep_member.port}",
                expected=f"member of {ep_bridge.port}",
                observed=None,
                source=ObservationSource.DECLARED,
                flag="missing",
                message=f"Bridge member port '{ep_member.port}' not found in observed topology",
            )
        )

    return checks


def _verify_vlan_parent(
    link: Link,
    declared: TopologySnapshot,
    observed: TopologySnapshot,
) -> list[CheckResult]:
    checks: list[CheckResult] = []
    ep_child, ep_parent = link.endpoints

    parent_port = _get_port(observed, ep_parent.device, ep_parent.port)
    if parent_port is not None and parent_port.vlans is not None:
        child_port = _get_port(declared, ep_child.device, ep_child.port)
        if child_port is not None and child_port.vlans is not None:
            vlan_id = child_port.vlans.access_vlan or child_port.vlans.native
            if vlan_id is not None and vlan_id in parent_port.vlans.tagged:
                checks.append(
                    CheckResult(
                        check="vlan_on_parent",
                        port=f"{ep_child.device}/{ep_child.port}",
                        expected=f"VLAN {vlan_id} on parent {ep_parent.port}",
                        observed=f"VLAN {vlan_id} present",
                        source=ObservationSource.MCP_LIVE,
                        flag="ok",
                    )
                )
            elif vlan_id is not None:
                checks.append(
                    CheckResult(
                        check="vlan_on_parent",
                        port=f"{ep_child.device}/{ep_child.port}",
                        expected=f"VLAN {vlan_id} on parent {ep_parent.port}",
                        observed=f"VLAN {vlan_id} not found",
                        source=ObservationSource.MCP_LIVE,
                        flag="mismatch",
                        message=f"VLAN {vlan_id} not carried on parent port",
                    )
                )

    return checks


def _check_vlan_compatibility(
    port_a: Port,
    port_b: Port,
    ep_a: object,
    ep_b: object,
) -> list[CheckResult]:
    checks: list[CheckResult] = []

    if port_a.vlans is None or port_b.vlans is None:
        return checks

    va, vb = port_a.vlans, port_b.vlans
    port_label_a = f"{getattr(ep_a, 'device', '?')}/{getattr(ep_a, 'port', '?')}"
    port_label_b = f"{getattr(ep_b, 'device', '?')}/{getattr(ep_b, 'port', '?')}"

    if va.mode == "trunk" and vb.mode == "trunk":
        shared = set(va.tagged) & set(vb.tagged)
        if not shared and (va.tagged or vb.tagged):
            checks.append(
                CheckResult(
                    check="vlan_compatibility",
                    port=port_label_a,
                    expected=f"shared VLANs with {port_label_b}",
                    observed=f"no shared VLANs (A={va.tagged}, B={vb.tagged})",
                    source=ObservationSource.DECLARED,
                    flag="warning",
                    message="Trunk ports have no shared tagged VLANs",
                )
            )
        else:
            checks.append(
                CheckResult(
                    check="vlan_compatibility",
                    port=port_label_a,
                    expected=f"shared VLANs with {port_label_b}",
                    observed=f"shared: {sorted(shared)}",
                    source=ObservationSource.DECLARED,
                    flag="ok",
                )
            )

    elif va.mode == "access" and vb.mode == "access":
        if va.access_vlan != vb.access_vlan:
            checks.append(
                CheckResult(
                    check="vlan_compatibility",
                    port=port_label_a,
                    expected=f"same access VLAN as {port_label_b}",
                    observed=f"A={va.access_vlan}, B={vb.access_vlan}",
                    source=ObservationSource.DECLARED,
                    flag="mismatch",
                    message="Access ports on different VLANs",
                )
            )
        else:
            checks.append(
                CheckResult(
                    check="vlan_compatibility",
                    port=port_label_a,
                    expected=f"VLAN {va.access_vlan}",
                    observed=f"VLAN {vb.access_vlan}",
                    source=ObservationSource.DECLARED,
                    flag="ok",
                )
            )

    return checks


# --- Helpers ---


def _get_port(
    snapshot: TopologySnapshot,
    device: str,
    port: str,
) -> Port | None:
    dev = snapshot.devices.get(device)
    if dev is None:
        return None
    return dev.ports.get(port)


def _link_status(checks: list[CheckResult]) -> str:
    flags = {c.flag for c in checks}
    if "missing" in flags or "mismatch" in flags:
        return "fail"
    if "warning" in flags:
        return "warning"
    return "pass"


def _highest_severity(checks: list[CheckResult]) -> CheckSeverity:
    if not checks:
        return CheckSeverity.INFO
    return min(checks, key=lambda c: _SEVERITY_ORDER.get(c.severity, 9)).severity


def _build_summary(results: list[LinkVerification]) -> dict[str, Any]:
    link_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()

    for r in results:
        link_counts[r.status] += 1
        for c in r.checks:
            severity_counts[c.severity] += 1
            if c.category:
                category_counts[c.category] += 1

    highlights = _build_highlights(len(results), link_counts, category_counts)

    return {
        "total": len(results),
        "pass": link_counts.get("pass", 0),
        "fail": link_counts.get("fail", 0),
        "warning": link_counts.get("warning", 0),
        "by_category": dict(category_counts),
        "by_severity": dict(severity_counts),
        "highlights": highlights,
    }


def _build_highlights(
    total: int,
    link_counts: Counter[str],
    category_counts: Counter[str],
) -> list[str]:
    if total == 0:
        return ["No links to verify"]

    fail_count = link_counts.get("fail", 0)
    warn_count = link_counts.get("warning", 0)

    if fail_count == 0 and warn_count == 0:
        return [f"All {total} links pass verification"]

    highlights: list[str] = []

    if fail_count > 0:
        highlights.append(f"{fail_count} of {total} links failed")

    if warn_count > 0:
        highlights.append(f"{warn_count} of {total} links have warnings")

    # Add category-specific detail, sorted by count descending
    for cat, count in category_counts.most_common():
        label = cat.replace("_", " ")
        highlights.append(f"{count} {label}")

    return highlights
