"""Print job ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from logistics_app.data.models.base import Base
from logistics_app.data.models.enums import DocumentType, PrintJobStatus, PrintTargetType
from logistics_app.data.models.sql_types import enum_column_type


class PrintJob(Base):
    """Tracks a print request and its operational outcome."""

    __tablename__ = "print_jobs"
    __table_args__ = (
        CheckConstraint(
            "delivery_slip_id is not null or document_id is not null or split_transport_id is not null",
            name="print_job_has_target_reference",
        ),
        CheckConstraint("requested_copy_count >= 1", name="requested_copy_count_positive"),
        CheckConstraint("printed_copy_count is null or printed_copy_count >= 0", name="printed_copy_count_not_negative"),
        Index("ix_print_jobs_printer_name_queued_at", "printer_name", "queued_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    delivery_slip_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("delivery_slips.id", ondelete="SET NULL"),
        index=True,
    )
    document_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("documents.id", ondelete="SET NULL"),
        index=True,
    )
    document_type: Mapped[DocumentType] = mapped_column(
        enum_column_type(DocumentType, "document_type"),
        index=True,
    )
    split_transport_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("split_transports.id", ondelete="SET NULL"),
        index=True,
    )
    target_type: Mapped[PrintTargetType] = mapped_column(
        enum_column_type(PrintTargetType, "print_target_type")
    )
    printer_role: Mapped[str | None] = mapped_column(String(50))
    printer_name: Mapped[str] = mapped_column(String(200))
    is_manual_printer_override: Mapped[bool] = mapped_column(Boolean(), default=False)
    requested_copy_count: Mapped[int] = mapped_column(Integer())
    printed_copy_count: Mapped[int | None] = mapped_column(Integer())
    reprint_of_print_job_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("print_jobs.id", ondelete="SET NULL"),
        index=True,
    )
    status: Mapped[PrintJobStatus] = mapped_column(
        enum_column_type(PrintJobStatus, "print_job_status"),
        index=True,
    )
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_by: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    delivery_slip: Mapped["DeliverySlip | None"] = relationship(back_populates="print_jobs")
    document: Mapped["Document | None"] = relationship(back_populates="print_jobs")
    split_transport: Mapped["SplitTransport | None"] = relationship(back_populates="print_jobs")
    reprint_of_print_job: Mapped["PrintJob | None"] = relationship(remote_side=[id])
