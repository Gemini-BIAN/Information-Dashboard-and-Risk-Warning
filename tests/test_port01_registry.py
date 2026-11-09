from scm.ports.registry import initial_snapshot, registry, source_specs
from scm.settings import utcnow


def test_business_registry_retains_12_and_dover_not_london():
    ports = registry().ports
    assert len(ports) == 12 and all(p.watch_enabled for p in ports)
    assert "dover" in {p.id for p in ports} and "london" not in {p.id for p in ports}
    assert {"teesport", "middlesbrough", "tangier"} <= {p.id for p in ports}
    assert all(p.unlocode is None for p in ports)
    assert {s["id"] for s in source_specs()} >= {id for p in ports for id in p.source_ids}


def test_all_unknown_not_normal_without_evidence():
    for port in registry().ports:
        snap = initial_snapshot(port, utcnow())
        assert snap["state"] == "unknown" and snap["severity"] == "unknown" and not snap["events"]
        assert "未接入" in snap["metrics"]
    rotterdam = next(s for s in source_specs() if s["id"] == "rotterdam-restricted")
    assert rotterdam["permission"] == "blocked"
