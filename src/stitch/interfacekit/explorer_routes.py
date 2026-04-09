"""HTTP routes for the Explorer topology browser.

Exposes the ExplorerWorkflowProtocol as REST endpoints. Read-only queries
on the declared topology — neighbors, VLAN maps, diagnostics, trace, impact.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from stitch.modelkit.impact import ImpactRequest  # noqa: TC001 (FastAPI runtime)
from stitch.modelkit.trace import TraceRequest  # noqa: TC001 (FastAPI runtime)

_STATIC_DIR = Path(__file__).parent / "static"

if TYPE_CHECKING:
    from stitch.contractkit.explorer import ExplorerWorkflowProtocol


def create_explorer_router(workflow: ExplorerWorkflowProtocol) -> APIRouter:
    router = APIRouter(tags=["explorer"])

    @router.get("/topology")
    async def get_topology():
        snap = workflow.topology
        return snap.model_dump(mode="json")

    @router.get("/devices")
    async def list_devices():
        snap = workflow.topology
        return {
            dev_id: {
                "name": dev.name,
                "type": dev.type,
                "port_count": len(dev.ports),
                "management_ip": dev.management_ip,
            }
            for dev_id, dev in sorted(snap.devices.items())
        }

    @router.get("/devices/{device_id}")
    async def get_device(device_id: str):
        snap = workflow.topology
        device = snap.devices.get(device_id)
        if device is None:
            raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
        return device.model_dump(mode="json")

    @router.get("/devices/{device_id}/neighbors")
    async def get_neighbors(device_id: str):
        snap = workflow.topology
        if device_id not in snap.devices:
            raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
        nbrs = workflow.get_neighbors(device_id)
        return [n.model_dump(mode="json") for n in nbrs]

    @router.get("/vlans/{vlan_id}")
    async def get_vlan_ports(vlan_id: int):
        entries = workflow.get_vlan_ports(vlan_id)
        return [e.model_dump(mode="json") for e in entries]

    @router.get("/diagnostics")
    async def get_diagnostics():
        diag = workflow.get_diagnostics()
        return diag.model_dump(mode="json")

    @router.post("/trace")
    async def run_trace(request: TraceRequest):
        try:
            result = workflow.trace(request)
            return result.model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/impact")
    async def run_impact(request: ImpactRequest):
        try:
            result = workflow.impact(request)
            return result.model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/ui", response_class=HTMLResponse)
    async def explorer_ui():
        html_path = _STATIC_DIR / "explorer.html"
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))

    return router
