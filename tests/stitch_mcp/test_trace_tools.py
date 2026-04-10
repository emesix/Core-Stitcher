"""Tests for trace and impact preview MCP tools."""

import asyncio
import json

from fastmcp import FastMCP

from stitch.mcp.engine import StitchEngine
from stitch.mcp.schemas import ErrorCode
from stitch.mcp.tools.trace import register_trace_tools


def _get_tool_fn(mcp: FastMCP, name: str):
    tool = asyncio.run(mcp.get_tool(name))
    return tool.fn


class TestStitchTraceVlan:
    def test_returns_ok_response(self, engine):
        mcp = FastMCP("test")
        register_trace_tools(mcp, engine)
        fn = _get_tool_fn(mcp, "stitch_trace_vlan")

        raw = fn(vlan=100)
        resp = json.loads(raw)
        assert resp["ok"] is True
        assert "result" in resp
        assert resp["result"]["vlan"] == 100
        assert "status" in resp["result"]
        assert "hops" in resp["result"]

    def test_trace_with_source(self, engine):
        mcp = FastMCP("test")
        register_trace_tools(mcp, engine)
        fn = _get_tool_fn(mcp, "stitch_trace_vlan")

        raw = fn(vlan=100, source="sw01")
        resp = json.loads(raw)
        assert resp["ok"] is True
        assert resp["result"]["source"] == "sw01"

    def test_summary_includes_status_and_hops(self, engine):
        mcp = FastMCP("test")
        register_trace_tools(mcp, engine)
        fn = _get_tool_fn(mcp, "stitch_trace_vlan")

        raw = fn(vlan=100)
        resp = json.loads(raw)
        assert "VLAN 100" in resp["summary"]
        assert "hops" in resp["summary"]

    def test_invalid_topology_returns_error(self, tmp_path):
        bad_engine = StitchEngine(
            topology_path=str(tmp_path / "nonexistent.json"),
            gateway_url="http://localhost:4444",
        )
        mcp = FastMCP("test")
        register_trace_tools(mcp, bad_engine)
        fn = _get_tool_fn(mcp, "stitch_trace_vlan")

        raw = fn(vlan=100)
        resp = json.loads(raw)
        assert resp["ok"] is False
        assert resp["error"]["code"] == ErrorCode.TOPOLOGY_NOT_FOUND


class TestStitchImpactPreview:
    def test_returns_ok_with_risk(self, engine):
        mcp = FastMCP("test")
        register_trace_tools(mcp, engine)
        fn = _get_tool_fn(mcp, "stitch_impact_preview")

        raw = fn(action="remove_port", device="sw01", port="sfp-sfpplus1")
        resp = json.loads(raw)
        assert resp["ok"] is True
        assert "result" in resp
        assert "risk" in resp["result"]
        assert "safe_to_apply" in resp["result"]
        assert "impact" in resp["result"]

    def test_impact_with_json_parameters(self, engine):
        mcp = FastMCP("test")
        register_trace_tools(mcp, engine)
        fn = _get_tool_fn(mcp, "stitch_impact_preview")

        params_json = json.dumps({"link_id": "link-sw01-fw01"})
        raw = fn(action="remove_link", device="sw01", parameters=params_json)
        resp = json.loads(raw)
        assert resp["ok"] is True
        assert resp["result"]["proposed_change"]["action"] == "remove_link"

    def test_impact_summary_includes_risk(self, engine):
        mcp = FastMCP("test")
        register_trace_tools(mcp, engine)
        fn = _get_tool_fn(mcp, "stitch_impact_preview")

        raw = fn(action="remove_port", device="sw01", port="sfp-sfpplus1")
        resp = json.loads(raw)
        assert "risk" in resp["summary"]
        assert "effect" in resp["summary"]

    def test_impact_invalid_topology(self, tmp_path):
        bad_engine = StitchEngine(
            topology_path=str(tmp_path / "nonexistent.json"),
            gateway_url="http://localhost:4444",
        )
        mcp = FastMCP("test")
        register_trace_tools(mcp, bad_engine)
        fn = _get_tool_fn(mcp, "stitch_impact_preview")

        raw = fn(action="remove_port", device="sw01")
        resp = json.loads(raw)
        assert resp["ok"] is False
        assert resp["error"]["code"] == ErrorCode.TOPOLOGY_NOT_FOUND

    def test_impact_with_invalid_parameters_json(self, engine):
        mcp = FastMCP("test")
        register_trace_tools(mcp, engine)
        fn = _get_tool_fn(mcp, "stitch_impact_preview")

        raw = fn(action="remove_port", device="sw01", parameters="not-valid-json")
        resp = json.loads(raw)
        assert resp["ok"] is False
        assert resp["error"]["code"] == ErrorCode.TOPOLOGY_INVALID
