"""Application log ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, JSON, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from logistics_app.data.models.base import Base
from logistics_app.data.models.enums import ApplicationLogLevel
from logistics_app.data.models.sql_types import enum_column_type


class ApplicationLog(Base):
    """Persisted technical log record for diagnostics and support."""

    __tablename__ = "application_logs"
    __table_args__ = (
        CheckConstraint("char_length(trim(message)) > 0", name="message_not_blank"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    log_level: Mapped[ApplicationLogLevel] = mapped_column(
        enum_column_type(ApplicationLogLevel, "application_log_level"),
        index=True,
    )
    logger_name: Mapped[str] = mapped_column(String(200), index=True)
    message: Mapped[str] = mapped_column(Text())
    exception_type: Mapped[str | None] = mapped_column(String(200))
    exception_message: Mapped[str | None] = mapped_column(Text())
    context_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON())
    delivery_slip_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("delivery_slips.id", ondelete="SET NULL"),
        index=True,
    )
    pallet_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("pallets.id", ondelete="SET NULL"),
        index=True,
    )
    document_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("documents.id", ondelete="SET NULL"),
        index=True,
    )
    request_id: Mapped[str | None] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    delivery_slip: Mapped["DeliverySlip | None"] = relationship(back_populates="application_logs")
    pallet: Mapped["Pallet | None"] = relationship(back_populates="application_logs")
    document: Mapped["Document | None"] = relationship(back_populates="application_logs")
