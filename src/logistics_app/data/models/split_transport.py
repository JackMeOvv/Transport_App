"""Split transport ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from logistics_app.data.models.base import Base
from logistics_app.data.models.enums import SplitTransportStatus
from logistics_app.data.models.sql_types import enum_column_type


class SplitTransport(Base):
    """Optional extension used only when one delivery is split across transports."""

    __tablename__ = "split_transports"
    __table_args__ = (
        CheckConstraint("sequence_number >= 1", name="sequence_number_positive"),
        CheckConstraint("char_length(trim(split_code)) > 0", name="split_code_not_blank"),
        UniqueConstraint("delivery_slip_id", "split_code"),
        UniqueConstraint("delivery_slip_id", "sequence_number"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    delivery_slip_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("delivery_slips.id", ondelete="RESTRICT"),
        index=True,
    )
    split_code: Mapped[str] = mapped_column(String(50))
    transport_reference: Mapped[str | None] = mapped_column(String(100))
    sequence_number: Mapped[int] = mapped_column(Integer())
    status: Mapped[SplitTransportStatus] = mapped_column(
        enum_column_type(SplitTransportStatus, "split_transport_status")
    )
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(String(100))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(100))

    delivery_slip: Mapped["DeliverySlip"] = relationship(back_populates="split_transports")
    pallets: Mapped[list["Pallet"]] = relationship(back_populates="split_transport")
    documents: Mapped[list["Document"]] = relationship(back_populates="split_transport")
    document_print_instructions: Mapped[list["DocumentPrintInstruction"]] = relationship(
        back_populates="split_transport"
    )
    print_jobs: Mapped[list["PrintJob"]] = relationship(back_populates="split_transport")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="split_transport")
