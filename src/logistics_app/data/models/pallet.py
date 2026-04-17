"""Pallet ORM model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from logistics_app.data.models.base import Base
from logistics_app.data.models.enums import PalletStatus
from logistics_app.data.models.sql_types import enum_column_type


class Pallet(Base):
    """Physical pallet or package unit belonging to a delivery."""

    __tablename__ = "pallets"
    __table_args__ = (
        CheckConstraint("char_length(trim(pallet_identifier)) > 0", name="pallet_identifier_not_blank"),
        CheckConstraint("package_count is null or package_count >= 0", name="package_count_not_negative"),
        CheckConstraint("gross_weight_kg is null or gross_weight_kg >= 0", name="gross_weight_not_negative"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    delivery_slip_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("delivery_slips.id", ondelete="RESTRICT"),
        index=True,
    )
    pallet_identifier: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    split_transport_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("split_transports.id", ondelete="RESTRICT"),
        index=True,
    )
    current_warehouse_location_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("warehouse_locations.id", ondelete="SET NULL"),
        index=True,
    )
    status: Mapped[PalletStatus] = mapped_column(
        enum_column_type(PalletStatus, "pallet_status"),
        index=True,
    )
    gross_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    package_count: Mapped[int | None] = mapped_column(Integer())
    description: Mapped[str | None] = mapped_column(String(255))
    loaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(String(100))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(100))

    delivery_slip: Mapped["DeliverySlip"] = relationship(back_populates="pallets")
    split_transport: Mapped["SplitTransport | None"] = relationship(back_populates="pallets")
    current_warehouse_location: Mapped["WarehouseLocation | None"] = relationship(
        back_populates="pallets"
    )
    documents: Mapped[list["Document"]] = relationship(back_populates="pallet")
    pallet_movements: Mapped[list["PalletMovement"]] = relationship(back_populates="pallet")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="pallet")
    application_logs: Mapped[list["ApplicationLog"]] = relationship(back_populates="pallet")
