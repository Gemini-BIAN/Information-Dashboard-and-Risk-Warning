from datetime import timedelta

from sqlalchemy import select

from scm.database.models import PortSignal
from scm.ports.engine import Notice
from scm.ports.service import store_notice
from scm.settings import utcnow


def seed(factory):
    """Explicit opt-in Demo only. Never called by Live collection or snapshots."""
    now = utcnow()
    source = {
        "id": "demo",
        "name": "DEMO 虚构港口公告",
        "url": "https://example.invalid/port-demo",
        "ports": ["teesport", "middlesbrough", "dover"],
        "audit_ref": "DEMO fictional",
    }
    samples = [
        (
            "DEMO-TEES-01",
            "DEMO River Tees port closure",
            "Fictional demonstration: River Tees port is closed. ISO Tank dangerous goods acceptance is restricted.",
            now - timedelta(hours=1),
        ),
        (
            "DEMO-DOVER-02",
            "DEMO Dover dangerous goods restriction",
            "Fictional demonstration: Dover dangerous goods acceptance is restricted. The change is planned for tomorrow.",
            now + timedelta(days=1),
        ),
    ]
    with factory.begin() as session:
        for id, title, body, start in samples:
            if session.scalar(
                select(PortSignal).where(PortSignal.external_id == id, PortSignal.data_mode == "demo")
            ):
                continue
            store_notice(
                session,
                source,
                Notice(
                    external_id=id,
                    title=title,
                    body=body,
                    url="https://example.invalid/port-demo/" + id,
                    published_at=now - timedelta(hours=1),
                    fetched_at=now,
                    valid_from=start,
                    valid_until=now + timedelta(days=2),
                    data_mode="demo",
                    verification_type="DEMO",
                ),
            )
