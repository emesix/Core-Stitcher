"""Interface write-path tools — OPNsense interface assignment."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from stitch.mcp.services.interface_service import InterfaceService

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from stitch.mcp.engine import StitchEngine


def register_interface_tools(mcp: FastMCP, engine: StitchEngine) -> None:
    svc = InterfaceService(engine)

    @mcp.tool()
    def stitch_interface_assign(
        device_id: str,
        physical_interface: str,
        assign_as: str,
        description: str | None = None,
        dry_run: bool = True,
    ) -> str:
        """Assign an OPNsense physical interface to a logical role.

        Args:
            device_id: Device ID from topology (e.g. "fw01").
            physical_interface: Physical interface name (e.g. "ix0").
            assign_as: Logical assignment name (e.g. "opt1", "lan", "wan").
            description: Optional human-readable description.
            dry_run: If True (default), show projected state without applying.
        """
        resp = asyncio.run(
            svc.assign(
                device_id,
                physical_interface,
                assign_as,
                description,
                dry_run=dry_run,
            )
        )
        return json.dumps(resp.to_dict())
