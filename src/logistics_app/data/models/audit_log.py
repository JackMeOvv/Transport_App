"""Audit log ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, JSON, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from logistics_app.data.models.base import Base
from logistics_app.data.models.enums import AuditActionType, AuditEntityType
from logistics_app.data.models.sql_types import enum_column_type


class AuditLog(Base):
    """Business audit trail for traceable operational actions."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity_type_entity_id_occurred_at", "entity_type", "entity_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    entity_type: Mapped[AuditEntityType] = mapped_column(
        enum_column_type(AuditEntityType, "audit_entity_type"),
        index=True,
    )
    entity_id: Mapped[int | None] = mapped_column(BigInteger)
    action_type: Mapped[AuditActionType] = mapped_column(
        enum_column_type(AuditActionType, "audit_action_type")
    )
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
    split_transport_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("split_transports.id", ondelete="SET NULL"),
        index=True,
    )
    performed_by: Mapped[str | None] = mapped_column(String(100), index=True)
    source_system: Mapped[str | None] = mapped_column(String(100))
    details_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    delivery_slip: Mapped["DeliverySlip | None"] = relationship(back_populates="audit_logs")
    pallet: Mapped["Pallet | None"] = relationship(back_populates="audit_logs")
    document: Mapped["Document | None"] = relationship(back_populates="audit_logs")
    split_transport: Mapped["SplitTransport | None"] = relationship(back_populates="audit_logs")
