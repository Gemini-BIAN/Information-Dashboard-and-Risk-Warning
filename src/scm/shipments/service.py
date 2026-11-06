import csv
import io
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from scm.database.models import ShipmentSnapshot, Event
from scm.risk.rules import normalize_port
from scm.settings import utcnow
import json

COLUMNS = ['Container Number', 'Vessel', 'Voyage', 'Shipping Line', 'POL', 'POD', 'ETD', 'ETA', 'ATD', 'ATA', 'Status', 'Updated At']


class ShipmentRow(BaseModel):
    container_number: str = Field(min_length=1, max_length=50)
    vessel: str = Field(min_length=1, max_length=150)
    voyage: str = Field(min_length=1, max_length=100)
    shipping_line: str = Field(min_length=1, max_length=150)
    pol: str = Field(min_length=1, max_length=100)
    pod: str = Field(min_length=1, max_length=100)
    etd: datetime | None = None
    eta: datetime
    atd: datetime | None = None
    ata: datetime | None = None
    status: str = Field(min_length=1, max_length=100)
    updated_at: datetime

    @model_validator(mode='after')
    def timezone_required(self):
        for name in ['etd', 'eta', 'atd', 'ata', 'updated_at']:
            value = getattr(self, name)
            if value and value.tzinfo is None:
                raise ValueError(f'{name} requires explicit timezone, e.g. Z or +08:00')
            if value:
                setattr(self, name, value.astimezone(timezone.utc))
        return self


def import_csv(session, content, mode):
    if mode not in ['demo', 'live']:
        raise ValueError('mode must be demo/live')
    if len(content) > 5_000_000:
        raise ValueError('CSV exceeds 5MB')
    reader = csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
    if reader.fieldnames != COLUMNS:
        raise ValueError('CSV headers must match provided template exactly')
    rows = []
    for index, raw in enumerate(reader, 2):
        if index > 10001:
            raise ValueError('CSV exceeds 10,000 rows')
        if None in raw or any(v is None for v in raw.values()):
            raise ValueError(f'Row {index}: incorrect field count')
        values = {k.lower().replace(' ', '_'): v.strip() or None for k, v in raw.items()}
        try:
            row = ShipmentRow.model_validate(values)
            if mode == 'demo' and not row.container_number.startswith('DEMO-'):
                raise ValueError('Demo imports require DEMO- identifiers')
            if mode == 'live' and (row.container_number.startswith('DEMO-') or row.vessel.startswith('DEMO')):
                raise ValueError('Demo identifiers cannot be imported as live')
            rows.append(row)
        except Exception as exc:
            raise ValueError(f'Row {index}: {exc}') from exc
    # Validate all rows before writing. Transaction also protects conflicts across rows.
    inserted = skipped = 0
    for row in rows:
        values = row.model_dump()
        values['pol'], values['pod'] = normalize_port(row.pol), normalize_port(row.pod)
        for key in ['etd', 'eta', 'atd', 'ata', 'updated_at']:
            values[key] = values[key].isoformat() if values[key] else None
        key_fields = ['container_number', 'vessel', 'voyage', 'pol', 'pod', 'updated_at']
        existing = session.scalar(select(ShipmentSnapshot).where(ShipmentSnapshot.data_mode == mode, *[getattr(ShipmentSnapshot, key) == values[key] for key in key_fields]))
        if existing:
            if any(getattr(existing, k) != v for k, v in values.items()):
                raise ValueError('Conflicting snapshot at same Updated At; supply a new timestamp')
            skipped += 1
            continue
        session.add(ShipmentSnapshot(**values, data_mode=mode, imported_at=utcnow().isoformat()))
        session.flush()
        inserted += 1
    return {'inserted': inserted, 'unchanged': skipped}


def shipment_key(snapshot):
    return (snapshot.container_number, snapshot.vessel, snapshot.voyage, snapshot.pol, snapshot.pod)


def shipment_risks(session, mode):
    groups = {}
    for row in session.scalars(select(ShipmentSnapshot).where(ShipmentSnapshot.data_mode == mode).order_by(ShipmentSnapshot.updated_at, ShipmentSnapshot.id)):
        groups.setdefault(shipment_key(row), []).append(row)
    events = list(session.scalars(select(Event).where(Event.data_mode == mode, Event.review_status != 'rejected')))
    output = []
    for rows in groups.values():
        current = rows[-1]
        eta = datetime.fromisoformat(current.eta)
        previous_delta = (eta - datetime.fromisoformat(rows[-2].eta)).total_seconds() / 3600 if len(rows) > 1 else None
        baseline_delta = (eta - datetime.fromisoformat(rows[0].eta)).total_seconds() / 3600 if len(rows) > 1 else None
        level = '未知' if previous_delta is None else '高' if previous_delta >= 72 else '中' if previous_delta >= 24 else '低'
        reasons = ['仅一个快照，无法计算ETA变化'] if previous_delta is None else [f'相对上一快照ETA变化 {previous_delta:+.1f} 小时；阈值：24h中，72h高。']
        if current.ata:
            level = '低'
            reasons.append('已有ATA，当前航段标记到港；历史ETA变化仍保留。')
        window_start = datetime.fromisoformat(current.atd or current.etd or current.updated_at) - timedelta(days=7)
        window_end = datetime.fromisoformat(current.ata or current.eta) + timedelta(days=7)
        linked = []
        for event in events:
            if event.published_at is None or event.event_type not in ['港口运营', '航线调整']:
                continue
            if current.pod in json.loads(event.ports_json) and window_start <= datetime.fromisoformat(event.published_at) <= window_end:
                linked.append({'event_id': event.id, 'title': event.title, 'url': event.canonical_url, 'association': '待核实：仅按POD与公告发布时间窗口匹配，无承运人/航次确认'})
        if linked:
            reasons.append('存在港口公告候选关联，待核实；不构成甩柜、跳港或延误的直接证据。')
        stale = (utcnow() - datetime.fromisoformat(current.updated_at)).total_seconds() > 48 * 3600
        if stale:
            reasons.append('快照超过48小时未更新，需核实最新船期。')
        output.append({'container_number': current.container_number, 'vessel': current.vessel, 'voyage': current.voyage, 'pod': current.pod, 'eta': current.eta, 'ata': current.ata, 'snapshot_count': len(rows), 'previous_delta_hours': previous_delta, 'baseline_delta_hours': baseline_delta, 'risk_level': level, 'reasons': reasons, 'linked_events': linked, 'updated_at': current.updated_at, 'data_mode': mode})
    return output
