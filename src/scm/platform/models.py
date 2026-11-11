from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from scm.database.models import Base


class PlatformSource(Base):
    __tablename__ = "platform_sources"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    spec_json: Mapped[str] = mapped_column(Text)
    last_checked_at: Mapped[str | None] = mapped_column(String)
    last_success_at: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="unavailable")


class Item(Base):
    __tablename__ = "platform_items"
    __table_args__ = (UniqueConstraint("source_id", "external_id", "mode"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("platform_sources.id"))
    external_id: Mapped[str] = mapped_column(String)
    mode: Mapped[str] = mapped_column(String)
    module: Mapped[str] = mapped_column(String)
    version: Mapped[int] = mapped_column(default=0)
    review_status: Mapped[str] = mapped_column(String, default="pending")
    updated_at: Mapped[str] = mapped_column(String)


class Evidence(Base):
    __tablename__ = "platform_evidence"
    __table_args__ = (UniqueConstraint("item_id", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("platform_items.id"))
    version: Mapped[int] = mapped_column()
    raw_json: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String)
    captured_at: Mapped[str] = mapped_column(String)


class Assessment(Base):
    __tablename__ = "platform_assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("platform_evidence.id"), unique=True)
    analyzed_at: Mapped[str] = mapped_column(String)
    payload_json: Mapped[str] = mapped_column(Text)


class Alert(Base):
    __tablename__ = "platform_alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("platform_evidence.id"), unique=True)
    mode: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[str] = mapped_column(String)


class Audit(Base):
    __tablename__ = "platform_audits"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String)
    mode: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)
    payload_json: Mapped[str] = mapped_column(Text)


class Review(Base):
    __tablename__ = "platform_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("platform_items.id"))
    version: Mapped[int] = mapped_column()
    created_at: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(Text)


class Report(Base):
    __tablename__ = "platform_reports"
    __table_args__ = (UniqueConstraint("mode", "kind", "period_start"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    mode: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    period_start: Mapped[str] = mapped_column(String)
    generated_at: Mapped[str] = mapped_column(String)
    html: Mapped[str] = mapped_column(Text)
