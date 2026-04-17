"""Document print instruction ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    BigInteger,
    CheckConstraint,
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
from logistics_app.data.models.enums import DocumentType
from logistics_app.data.models.sql_types import enum_column_type


class DocumentPrintInstruction(Base):
    """Required print copies for a document type on a delivery or split transport."""

    __tablename__ = "document_print_instructions"
    __table_args__ = (
        CheckConstraint("required_copy_count >= 0", name="required_copy_count_not_negative"),
        UniqueConstraint("delivery_slip_id", "split_transport_id", "document_type", "printer_role"),
        Index(
            "ix_document_print_instructions_delivery_slip_id_document_type",
            "delivery_slip_id",
            "document_type",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    delivery_slip_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("delivery_slips.id", ondelete="RESTRICT"),
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
    required_copy_count: Mapped[int] = mapped_column(Integer())
    printer_role: Mapped[str | None] = mapped_column(String(50))
    is_mandatory: Mapped[bool] = mapped_column(Boolean(), default=True)
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(String(100))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(100))

    delivery_slip: Mapped["DeliverySlip"] = relationship(back_populates="document_print_instructions")
    split_transport: Mapped["SplitTransport | None"] = relationship(
        back_populates="document_print_instructions"
    )
