from __future__ import annotations

from stitch.modelkit.enums import DeviceType, LinkType, ObservationSource, PortType, VlanMode


def test_device_type_values():
    assert DeviceType.SWITCH == "switch"
    assert DeviceType.PROXMOX == "proxmox"
    assert DeviceType.FIREWALL == "firewall"
    assert DeviceType.VM == "vm"
    assert DeviceType.CONTAINER == "container"
    assert DeviceType.ACCESSPOINT == "accesspoint"
    assert DeviceType.OTHER == "other"


def test_port_type_values():
    assert PortType.SFP_PLUS == "sfp+"
    assert PortType.ETHERNET == "ethernet"
    assert PortType.BRIDGE == "bridge"
    assert PortType.VLAN == "vlan"
    assert PortType.VIRTUAL == "virtual"


def test_link_type_values():
    assert LinkType.PHYSICAL_CABLE == "physical_cable"
    assert LinkType.BRIDGE_MEMBER == "bridge_member"
    assert LinkType.VLAN_PARENT == "vlan_parent"
    assert LinkType.INTERNAL_VIRTUAL == "internal_virtual"


def test_observation_source_values():
    assert ObservationSource.MCP_LIVE == "mcp_live"
    assert ObservationSource.DECLARED == "declared"
    assert ObservationSource.INFERRED == "inferred"
    assert ObservationSource.UNKNOWN == "unknown"


def test_vlan_mode_values():
    assert VlanMode.TRUNK == "trunk"
    assert VlanMode.ACCESS == "access"


def test_enums_are_str():
    assert isinstance(DeviceType.SWITCH, str)
    assert isinstance(PortType.ETHERNET, str)
    assert isinstance(LinkType.PHYSICAL_CABLE, str)
    assert isinstance(ObservationSource.MCP_LIVE, str)
    assert isinstance(VlanMode.TRUNK, str)
