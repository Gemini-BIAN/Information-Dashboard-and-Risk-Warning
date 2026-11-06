from sqlalchemy import String, Text, Integer, Float, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = 'sources'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(String)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[str | None] = mapped_column(String)
    last_status: Mapped[str] = mapped_column(String, default='NOT TESTED')
    audit_json: Mapped[str] = mapped_column(Text, default='{}')


class Event(Base):
    __tablename__ = 'events'
    __table_args__ = (UniqueConstraint('canonical_url', 'data_mode'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(ForeignKey('sources.id'))
    published_at: Mapped[str | None] = mapped_column(String)
    fetched_at: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)
    data_mode: Mapped[str] = mapped_column(String)
    content_hash: Mapped[str] = mapped_column(String, index=True)
    event_type: Mapped[str] = mapped_column(String)
    countries_json: Mapped[str] = mapped_column(Text)
    ports_json: Mapped[str] = mapped_column(Text)
    policy_status: Mapped[str] = mapped_column(String)
    effective_at: Mapped[str | None] = mapped_column(String)
    risk_level: Mapped[str] = mapped_column(String)
    risk_reasons_json: Mapped[str] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String, default='pending')
    topic: Mapped[str] = mapped_column(String)


class RawRevision(Base):
    __tablename__ = 'raw_revisions'
    __table_args__ = (UniqueConstraint('event_id', 'content_hash'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey('events.id'))
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    published_at: Mapped[str | None] = mapped_column(String)
    fetched_at: Mapped[str] = mapped_column(String)
    content_hash: Mapped[str] = mapped_column(String)


class Analysis(Base):
    __tablename__ = 'analyses'
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey('events.id'), index=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey('raw_revisions.id'))
    provider: Mapped[str] = mapped_column(String)
    analyzed_at: Mapped[str] = mapped_column(String)
    payload_json: Mapped[str] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)


class CollectionLog(Base):
    __tablename__ = 'collection_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('sources.id'))
    started_at: Mapped[str] = mapped_column(String)
    finished_at: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    collected: Mapped[int] = mapped_column(Integer, default=0)
    inserted: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    details_json: Mapped[str] = mapped_column(Text, default='{}')


class ReviewLog(Base):
    __tablename__ = 'review_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    target_type: Mapped[str] = mapped_column(String)
    target_id: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String)
    data_mode: Mapped[str] = mapped_column(String)


class PortOverride(Base):
    __tablename__ = 'port_overrides'
    __table_args__ = (UniqueConstraint('port', 'data_mode'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    port: Mapped[str] = mapped_column(String)
    data_mode: Mapped[str] = mapped_column(String)
    risk_level: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)
    expires_at: Mapped[str] = mapped_column(String)


class PortMetric(Base):
    __tablename__ = 'port_metrics'
    __table_args__ = (UniqueConstraint('port', 'observed_at', 'source_url', 'data_mode'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    port: Mapped[str] = mapped_column(String)
    observed_at: Mapped[str] = mapped_column(String)
    waiting_hours: Mapped[float] = mapped_column(Float)
    source_url: Mapped[str] = mapped_column(Text)
    data_mode: Mapped[str] = mapped_column(String)


class ShipmentSnapshot(Base):
    __tablename__ = 'shipment_snapshots'
    __table_args__ = (UniqueConstraint('container_number', 'vessel', 'voyage', 'pol', 'pod', 'updated_at', 'data_mode'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    container_number: Mapped[str] = mapped_column(String)
    vessel: Mapped[str] = mapped_column(String)
    voyage: Mapped[str] = mapped_column(String)
    shipping_line: Mapped[str] = mapped_column(String)
    pol: Mapped[str] = mapped_column(String)
    pod: Mapped[str] = mapped_column(String)
    etd: Mapped[str | None] = mapped_column(String)
    eta: Mapped[str] = mapped_column(String)
    atd: Mapped[str | None] = mapped_column(String)
    ata: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)
    imported_at: Mapped[str] = mapped_column(String)
    data_mode: Mapped[str] = mapped_column(String)


class Report(Base):
    __tablename__ = 'reports'
    __table_args__ = (UniqueConstraint('kind', 'period_start', 'period_end', 'data_mode'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String)
    period_start: Mapped[str] = mapped_column(String)
    period_end: Mapped[str] = mapped_column(String)
    data_mode: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)
    html: Mapped[str] = mapped_column(Text)
