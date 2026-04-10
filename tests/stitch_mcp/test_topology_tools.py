"""Tests for topology read tools via TopologyService."""

from stitch.mcp.schemas import DetailLevel, ErrorCode
from stitch.mcp.services.topology_service import TopologyService


class TestTopologySummary:
    def test_returns_ok_with_counts(self, engine):
        svc = TopologyService(engine)
        resp = svc.summary()
        assert resp.ok is True
        assert resp.result["device_count"] == 3
        assert resp.result["link_count"] == 2
        assert resp.result["vlan_count"] == 2

    def test_summary_includes_device_types(self, engine):
        svc = TopologyService(engine)
        resp = svc.summary()
        types = resp.result["device_types"]
        assert "switch" in types
        assert "firewall" in types
        assert "proxmox" in types


class TestDevices:
    def test_standard_detail(self, engine):
        svc = TopologyService(engine)
        resp = svc.devices()
        assert resp.ok is True
        devices = resp.result["devices"]
        assert len(devices) == 3
        sw = next(d for d in devices if d["id"] == "sw01")
        assert sw["model"] == "Mikrotik CRS309"
        assert sw["management_ip"] == "192.168.254.3"
        assert "ports" not in sw  # standard omits ports

    def test_summary_mode(self, engine):
        svc = TopologyService(engine)
        resp = svc.devices(detail=DetailLevel.SUMMARY)
        assert resp.ok is True
        devices = resp.result["devices"]
        sw = next(d for d in devices if d["id"] == "sw01")
        assert set(sw.keys()) == {"id", "name", "type"}

    def test_full_mode_includes_ports(self, engine):
        svc = TopologyService(engine)
        resp = svc.devices(detail=DetailLevel.FULL)
        devices = resp.result["devices"]
        sw = next(d for d in devices if d["id"] == "sw01")
        assert "ports" in sw
        assert len(sw["ports"]) == 3


class TestDeviceDetail:
    def test_returns_device_with_ports(self, engine):
        svc = TopologyService(engine)
        resp = svc.device_detail("sw01")
        assert resp.ok is True
        assert resp.result["device"]["id"] == "sw01"
        assert len(resp.result["device"]["ports"]) == 3

    def test_not_found(self, engine):
        svc = TopologyService(engine)
        resp = svc.device_detail("nonexistent")
        assert resp.ok is False
        assert resp.error["code"] == ErrorCode.DEVICE_NOT_FOUND


class TestDeviceNeighbors:
    def test_returns_neighbor_list(self, engine):
        svc = TopologyService(engine)
        resp = svc.device_neighbors("sw01")
        assert resp.ok is True
        neighbors = resp.result["neighbors"]
        assert len(neighbors) == 2
        neighbor_devices = {n["device"] for n in neighbors}
        assert neighbor_devices == {"fw01", "pve01"}

    def test_not_found(self, engine):
        svc = TopologyService(engine)
        resp = svc.device_neighbors("nonexistent")
        assert resp.ok is False
        assert resp.error["code"] == ErrorCode.DEVICE_NOT_FOUND

    def test_device_with_no_neighbors(self, engine):
        """fw01 only connects to sw01."""
        svc = TopologyService(engine)
        resp = svc.device_neighbors("fw01")
        assert resp.ok is True
        assert len(resp.result["neighbors"]) == 1


class TestDiagnostics:
    def test_returns_diagnostic_counts(self, engine):
        svc = TopologyService(engine)
        resp = svc.diagnostics()
        assert resp.ok is True
        result = resp.result
        assert result["total_devices"] == 3
        assert result["total_links"] == 2
        assert "dangling_ports" in result
        assert "orphan_devices" in result
        assert "missing_endpoints" in result

    def test_detects_dangling_ports(self, engine):
        """sfp-sfpplus2 on sw01 and ix1 on fw01 have no links."""
        svc = TopologyService(engine)
        resp = svc.diagnostics()
        dangling = resp.result["dangling_ports"]
        dangling_keys = {(d["device"], d["port"]) for d in dangling}
        assert ("sw01", "sfp-sfpplus2") in dangling_keys
        assert ("fw01", "ix1") in dangling_keys


class TestTopologyPathOverride:
    def test_summary_with_override(self, engine, topology_file):
        svc = TopologyService(engine)
        resp = svc.summary(topology_path=topology_file)
        assert resp.ok is True
        assert resp.topology_path == topology_file

    def test_file_not_found(self, engine):
        svc = TopologyService(engine)
        resp = svc.summary(topology_path="/nonexistent/path.json")
        assert resp.ok is False
        assert resp.error["code"] == ErrorCode.TOPOLOGY_NOT_FOUND
