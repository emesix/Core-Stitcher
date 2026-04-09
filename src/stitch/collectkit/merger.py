"""Core merge logic: observations → (TopologySnapshot, list[MergeConflict]).

Groups observations by device/port/field, detects conflicts when multiple
adapters disagree, and builds an observed TopologySnapshot.
"""

from __future__ import annotations

from collections import defaultdict

from vos.modelkit.device import Device
from vos.modelkit.enums import DeviceType, PortType
from vos.modelkit.observation import MergeConflict, Observation
from vos.modelkit.port import Port, VlanMembership
from vos.modelkit.topology import TopologyMeta, TopologySnapshot


def merge_observations(
    observations: list[Observation],
) -> tuple[TopologySnapshot, list[MergeConflict]]:
    conflicts: list[MergeConflict] = []

    # Group observations by (device, port, field)
    grouped: dict[tuple[str, str | None, str], list[Observation]] = defaultdict(list)
    for obs in observations:
        grouped[(obs.device, obs.port, obs.field)].append(obs)

    # Detect conflicts and pick winning values (first_source strategy)
    resolved: dict[tuple[str, str | None, str], Observation] = {}
    for key, obs_list in grouped.items():
        # Deduplicate by value — different adapters agreeing is not a conflict
        unique_values: dict[str, Observation] = {}
        for obs in obs_list:
            val_key = repr(obs.value)
            if val_key not in unique_values:
                unique_values[val_key] = obs

        if len(unique_values) > 1:
            conflicts.append(
                MergeConflict(
                    device=key[0],
                    port=key[1],
                    field=key[2],
                    sources=[obs.adapter or obs.source for obs in obs_list],
                    values=[obs.value for obs in obs_list],
                    resolution="first_source",
                )
            )

        # First observation wins (sorted by trust: mcp_live > declared > inferred > unknown)
        best = _pick_best(obs_list)
        resolved[key] = best

    # Build devices from resolved observations
    devices = _build_devices(resolved)

    snapshot = TopologySnapshot(
        meta=TopologyMeta(version="1.0", name="observed"),
        devices=devices,
    )
    return snapshot, conflicts


_SOURCE_PRIORITY = {"mcp_live": 0, "declared": 1, "inferred": 2, "unknown": 3}


def _pick_best(obs_list: list[Observation]) -> Observation:
    return min(obs_list, key=lambda o: _SOURCE_PRIORITY.get(o.source, 99))


def _build_devices(
    resolved: dict[tuple[str, str | None, str], Observation],
) -> dict[str, Device]:
    # Collect all device slugs
    device_slugs: set[str] = set()
    port_keys: dict[str, set[str]] = defaultdict(set)

    for (device, port, _field), _obs in resolved.items():
        device_slugs.add(device)
        if port is not None:
            port_keys[device].add(port)

    devices: dict[str, Device] = {}
    for slug in sorted(device_slugs):
        # Device-level fields
        device_type = _get_field(resolved, slug, None, "type", DeviceType.OTHER)
        device_name = _get_field(resolved, slug, None, "name", slug)
        mgmt_ip = _get_field(resolved, slug, None, "management_ip", None)
        model = _get_field(resolved, slug, None, "model", None)

        ports: dict[str, Port] = {}
        for port_alias in sorted(port_keys.get(slug, [])):
            port_type = _get_field(resolved, slug, port_alias, "type", PortType.ETHERNET)
            port_name = _get_field(resolved, slug, port_alias, "device_name", None)
            speed = _get_field(resolved, slug, port_alias, "speed", None)
            mac = _get_field(resolved, slug, port_alias, "mac", None)
            status = _get_field(resolved, slug, port_alias, "status", None)
            vlans_raw = _get_field(resolved, slug, port_alias, "vlans", None)

            vlans = None
            if vlans_raw is not None and isinstance(vlans_raw, dict):
                vlans = VlanMembership.model_validate(vlans_raw)

            ports[port_alias] = Port(
                type=port_type,
                device_name=port_name,
                speed=speed,
                mac=mac,
                description=status,
                vlans=vlans,
            )

        devices[slug] = Device(
            id=slug,
            name=device_name,
            type=device_type,
            model=model,
            management_ip=mgmt_ip,
            ports=ports,
        )

    return devices


def _get_field(
    resolved: dict[tuple[str, str | None, str], Observation],
    device: str,
    port: str | None,
    field: str,
    default: object = None,
) -> object:
    obs = resolved.get((device, port, field))
    if obs is not None:
        return obs.value
    return default
