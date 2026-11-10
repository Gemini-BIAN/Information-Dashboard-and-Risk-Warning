from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from scm.database.models import Base


class RegulationDocument(Base):
    __tablename__ = "regulatory_documents"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    metadata_json: Mapped[str] = mapped_column(Text)
    download_status: Mapped[str] = mapped_column(String, default="not_downloaded")
    parse_status: Mapped[str] = mapped_column(String, default="not_parsed")
    sha256: Mapped[str | None] = mapped_column(String)
    byte_size: Mapped[int | None] = mapped_column()
    local_path: Mapped[str | None] = mapped_column(Text)
    downloaded_at: Mapped[str | None] = mapped_column(String)
    verification_type: Mapped[str | None] = mapped_column(String)
    error: Mapped[str | None] = mapped_column(Text)
    quality_json: Mapped[str] = mapped_column(Text, default="[]")


class RegulationChunk(Base):
    __tablename__ = "regulatory_chunks"
    __table_args__ = (UniqueConstraint("document_id", "ordinal"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("regulatory_documents.id"))
    ordinal: Mapped[int] = mapped_column()
    unit_type: Mapped[str] = mapped_column(String)
    unit_label: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    page_start: Mapped[int | None] = mapped_column()
    page_end: Mapped[int | None] = mapped_column()
    locator: Mapped[str] = mapped_column(Text)
    quality_json: Mapped[str] = mapped_column(Text)
    terms_json: Mapped[str] = mapped_column(Text)


class RegulationAttempt(Base):
    __tablename__ = "regulatory_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("regulatory_documents.id"))
    attempted_at: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    details_json: Mapped[str] = mapped_column(Text)
