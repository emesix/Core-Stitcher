from stitch.core.queries import Filter, FilterOp, Query, QueryResult, parse_filter


def test_query_minimal():
    q = Query(resource_type="device")
    assert q.resource_id is None
    assert q.filters == []


def test_query_with_filters():
    q = Query(
        resource_type="device",
        filters=[Filter(field="type", op=FilterOp.EQ, value="SWITCH")],
        sort="-name",
        limit=10,
    )
    assert len(q.filters) == 1


def test_query_result():
    qr = QueryResult(
        items=[{"uri": "stitch:/device/dev_01", "name": "sw-core-01"}],
        total=1,
    )
    assert len(qr.items) == 1
    assert qr.next_cursor is None


def test_parse_filter_eq():
    f = parse_filter("type=SWITCH")
    assert f.field == "type"
    assert f.op == FilterOp.EQ
    assert f.value == "SWITCH"


def test_parse_filter_gte():
    f = parse_filter("severity>=WARNING")
    assert f.field == "severity"
    assert f.op == FilterOp.GTE
    assert f.value == "WARNING"


def test_parse_filter_contains():
    f = parse_filter("name~core")
    assert f.op == FilterOp.CONTAINS
    assert f.value == "core"


def test_parse_filter_comma_values():
    f = parse_filter("status=PENDING,RUNNING")
    assert f.op == FilterOp.IN
    assert f.value == ["PENDING", "RUNNING"]


def test_parse_filter_neq():
    f = parse_filter("status!=CANCELLED")
    assert f.op == FilterOp.NEQ
