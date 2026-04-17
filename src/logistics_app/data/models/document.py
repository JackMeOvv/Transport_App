"""Document ORM model."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from logistics_app.data.models.base import Base
from logistics_app.data.models.enums import DocumentStatus, DocumentType
from logistics_app.data.models.sql_types import enum_column_type


class Document(Base):
    """Metadata for operational files stored outside the database."""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("version_number >= 1", name="version_number_positive"),
        CheckConstraint("file_size_bytes is null or file_size_bytes >= 0", name="file_size_not_negative"),
        CheckConstraint(
            "document_status <> 'AVAILABLE' or storage_relative_path is not null",
            name="available_document_has_storage_path",
        ),
        UniqueConstraint(
            "delivery_slip_id",
            "pallet_id",
            "split_transport_id",
            "document_type",
            "version_number",
        ),
        Index("ix_documents_delivery_slip_id_document_type", "delivery_slip_id", "document_type"),
        Index(
            "ix_documents_delivery_slip_id_document_type_is_latest_version",
            "delivery_slip_id",
            "document_type",
            "is_latest_version",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    delivery_slip_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("delivery_slips.id", ondelete="RESTRICT"),
        index=True,
    )
    pallet_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("pallets.id", ondelete="SET NULL"),
        index=True,
    )
    split_transport_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("split_transports.id", ondelete="RESTRICT"),
        index=True,
    )
    document_type: Mapped[DocumentType] = mapped_column(
        enum_column_type(DocumentType, "document_type"),
        index=True,
    )
    document_status: Mapped[DocumentStatus] = mapped_column(
        enum_column_type(DocumentStatus, "document_status"),
        index=True,
    )
    original_filename: Mapped[str | None] = mapped_column(String(255))
    stored_filename: Mapped[str | None] = mapped_column(String(255))
    storage_relative_path: Mapped[str | None] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    uploaded_by: Mapped[str | None] = mapped_column(String(100))
    document_date: Mapped[date | None] = mapped_column(Date())
    version_number: Mapped[int] = mapped_column(Integer(), default=1)
    is_latest_version: Mapped[bool] = mapped_column(Boolean(), default=True)
    remarks: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    delivery_slip: Mapped["DeliverySlip"] = relationship(back_populates="documents")
    pallet: Mapped["Pallet | None"] = relationship(back_populates="documents")
    split_transport: Mapped["SplitTransport | None"] = relationship(back_populates="documents")
    print_jobs: Mapped[list["PrintJob"]] = relationship(back_populates="document")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="document")
    application_logs: Mapped[list["ApplicationLog"]] = relationship(back_populates="document")
