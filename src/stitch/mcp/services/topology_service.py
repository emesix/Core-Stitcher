"""TopologyService — read-only topology queries for MCP tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from stitch.mcp.schemas import DetailLevel, ErrorCode, ToolResponse

if TYPE_CHECKING:
    from stitch.mcp.engine import StitchEngine
    from stitch.modelkit.topology import TopologySnapshot


class TopologyService:
    def __init__(self, engine: StitchEngine) -> None:
        self._engine = engine

    def _load(
        self, topology_path: str | None
    ) -> tuple[TopologySnapshot | None, ToolResponse | None]:
        """Load topology, returning (snapshot, None) or (None, error)."""
        try:
            topo = self._engine.get_topology(override_path=topology_path)
        except FileNotFoundError:
            path = topology_path or self._engine.topology_path
            return None, ToolResponse.failure(
                ErrorCode.TOPOLOGY_NOT_FOUND,
                f"Topology file not found: {path}",
                summary="Topology file not found.",
                topology_path=path,
            )
        except Exception as exc:
            path = topology_path or self._engine.topology_path
            return None, ToolResponse.failure(
                ErrorCode.TOPOLOGY_INVALID,
                f"Failed to load topology: {exc}",
                summary="Topology file is invalid.",
                topology_path=path,
            )
        return topo, None

    def _resolve_path(self, topology_path: str | None) -> str:
        return topology_path or self._engine.topology_path

    def summary(self, topology_path: str | None = None) -> ToolResponse:
        topo, err = self._load(topology_path)
        if err:
            return err
        assert topo is not None

        device_types = sorted({str(d.type) for d in topo.devices.values()})
        result: dict[str, Any] = {
            "device_count": len(topo.devices),
            "link_count": len(topo.links),
            "vlan_count": len(topo.vlans),
            "device_types": device_types,
            "topology_name": topo.meta.name,
        }
        return ToolResponse.success(
            result,
            summary=(
                f"{len(topo.devices)} devices, {len(topo.links)} links,"
                f" {len(topo.vlans)} VLANs"
            ),
            topology_path=self._resolve_path(topology_path),
        )

    def devices(
        self,
        topology_path: str | None = None,
        detail: DetailLevel = DetailLevel.STANDARD,
    ) -> ToolResponse:
        topo, err = self._load(topology_path)
        if err:
            return err
        assert topo is not None

        devices: list[dict[str, Any]] = []
        for device in topo.devices.values():
            if detail == DetailLevel.SUMMARY:
                devices.append({"id": device.id, "name": device.name, "type": str(device.type)})
            elif detail == DetailLevel.STANDARD:
                d = device.model_dump(exclude={"ports", "position", "children"})
                d["type"] = str(d["type"])
                devices.append(d)
            else:  # FULL
                d = device.model_dump(exclude={"position"})
                d["type"] = str(d["type"])
                devices.append(d)

        return ToolResponse.success(
            {"devices": devices, "count": len(devices)},
            summary=f"{len(devices)} devices ({detail} detail)",
            topology_path=self._resolve_path(topology_path),
        )

    def device_detail(
        self, device_id: str, topology_path: str | None = None
    ) -> ToolResponse:
        topo, err = self._load(topology_path)
        if err:
            return err
        assert topo is not None

        device = topo.devices.get(device_id)
        if device is None:
            return ToolResponse.failure(
                ErrorCode.DEVICE_NOT_FOUND,
                f"Device '{device_id}' not found in topology.",
                summary=f"Device '{device_id}' not found.",
                topology_path=self._resolve_path(topology_path),
            )

        d = device.model_dump()
        d["type"] = str(d["type"])
        return ToolResponse.success(
            {"device": d},
            summary=f"Device {device.name} ({device.type}), {len(device.ports)} ports",
            topology_path=self._resolve_path(topology_path),
        )

    def device_neighbors(
        self, device_id: str, topology_path: str | None = None
    ) -> ToolResponse:
        topo, err = self._load(topology_path)
        if err:
            return err
        assert topo is not None

        if device_id not in topo.devices:
            return ToolResponse.failure(
                ErrorCode.DEVICE_NOT_FOUND,
                f"Device '{device_id}' not found in topology.",
                summary=f"Device '{device_id}' not found.",
                topology_path=self._resolve_path(topology_path),
            )

        explorer = self._engine.get_explorer(topology_path=topology_path)
        nbrs = explorer.get_neighbors(device_id)
        return ToolResponse.success(
            {
                "device_id": device_id,
                "neighbors": [n.model_dump() for n in nbrs],
                "count": len(nbrs),
            },
            summary=f"{len(nbrs)} neighbor(s) for {device_id}",
            topology_path=self._resolve_path(topology_path),
        )

    def diagnostics(self, topology_path: str | None = None) -> ToolResponse:
        topo, err = self._load(topology_path)
        if err:
            return err
        assert topo is not None  # noqa: S101

        explorer = self._engine.get_explorer(topology_path=topology_path)
        diag = explorer.get_diagnostics()
        result = diag.model_dump()
        return ToolResponse.success(
            result,
            summary=(
                f"{diag.total_devices} devices, {diag.total_links} links, "
                f"{len(diag.dangling_ports)} dangling, {len(diag.orphan_devices)} orphans"
            ),
            topology_path=self._resolve_path(topology_path),
        )
