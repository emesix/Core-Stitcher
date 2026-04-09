"""Tests for the output formatter."""
from stitch.apps.operator.output import OutputFormatter
from stitch.core.queries import QueryResult


def test_format_json():
    qr = QueryResult(items=[{"name": "sw-core-01", "type": "SWITCH"}], total=1)
    fmt = OutputFormatter("json")
    out = fmt.format_result(qr)
    assert '"name": "sw-core-01"' in out


def test_format_compact():
    qr = QueryResult(
        items=[
            {"uri": "stitch:/device/dev_01", "name": "sw-core-01", "status": None},
            {"uri": "stitch:/device/dev_02", "name": "sw-edge-01", "status": None},
        ],
        total=2,
    )
    fmt = OutputFormatter("compact")
    out = fmt.format_result(qr)
    lines = out.strip().split("\n")
    assert len(lines) == 2
    assert "\t" in lines[0]


def test_format_table():
    qr = QueryResult(
        items=[
            {"name": "sw-core-01", "type": "SWITCH", "ip": "192.168.254.2"},
        ],
        total=1,
    )
    fmt = OutputFormatter("table")
    out = fmt.format_result(qr)
    assert "sw-core-01" in out


def test_format_yaml():
    qr = QueryResult(items=[{"name": "sw-core-01"}], total=1)
    fmt = OutputFormatter("yaml")
    out = fmt.format_result(qr)
    assert "name:" in out or "name: sw-core-01" in out


def test_format_result_raw_json():
    fmt = OutputFormatter("json")
    out = fmt.format_result_raw({"vlan": 42, "status": "complete"})
    assert '"vlan": 42' in out


def test_format_human_single_item():
    qr = QueryResult(items=[{"name": "sw-core-01", "type": "SWITCH"}], total=1)
    fmt = OutputFormatter("human")
    out = fmt.format_result(qr)
    assert "name" in out
    assert "sw-core-01" in out


def test_format_human_multiple_items():
    qr = QueryResult(
        items=[
            {"name": "sw-core-01", "type": "SWITCH"},
            {"name": "sw-edge-01", "type": "SWITCH"},
        ],
        total=2,
    )
    fmt = OutputFormatter("human")
    out = fmt.format_result(qr)
    assert "sw-core-01" in out
    assert "sw-edge-01" in out


def test_format_compact_empty():
    qr = QueryResult(items=[], total=0)
    fmt = OutputFormatter("compact")
    out = fmt.format_result(qr)
    assert out.strip() == ""


def test_format_result_raw_yaml():
    fmt = OutputFormatter("yaml")
    out = fmt.format_result_raw({"vlan": 42, "status": "complete"})
    assert "vlan:" in out or "vlan: 42" in out
