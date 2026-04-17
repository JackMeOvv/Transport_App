"""Delivery slip ORM model."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from logistics_app.data.models.base import Base
from logistics_app.data.models.enums import DeliverySlipStatus
from logistics_app.data.models.sql_types import enum_column_type


class DeliverySlip(Base):
    """Main operational record for one delivery."""

    __tablename__ = "delivery_slips"
    __table_args__ = (
        CheckConstraint(
            "char_length(trim(delivery_slip_number)) > 0",
            name="delivery_slip_number_not_blank",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    delivery_slip_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    customer_reference: Mapped[str | None] = mapped_column(String(100))
    customer_name: Mapped[str | None] = mapped_column(String(200))
    delivery_date: Mapped[date | None] = mapped_column(Date(), index=True)
    origin_name: Mapped[str | None] = mapped_column(String(200))
    destination_name: Mapped[str | None] = mapped_column(String(200))
    transport_reference: Mapped[str | None] = mapped_column(String(100), index=True)
    status: Mapped[DeliverySlipStatus] = mapped_column(
        enum_column_type(DeliverySlipStatus, "delivery_slip_status"),
        index=True,
    )
    is_split_transport: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(String(100))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(100))

    split_transports: Mapped[list["SplitTransport"]] = relationship(back_populates="delivery_slip")
    pallets: Mapped[list["Pallet"]] = relationship(back_populates="delivery_slip")
    documents: Mapped[list["Document"]] = relationship(back_populates="delivery_slip")
    document_print_instructions: Mapped[list["DocumentPrintInstruction"]] = relationship(
        back_populates="delivery_slip"
    )
    print_jobs: Mapped[list["PrintJob"]] = relationship(back_populates="delivery_slip")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="delivery_slip")
    application_logs: Mapped[list["ApplicationLog"]] = relationship(back_populates="delivery_slip")
