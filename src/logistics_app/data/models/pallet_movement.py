"""Pallet movement ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from logistics_app.data.models.base import Base
from logistics_app.data.models.enums import PalletMovementType
from logistics_app.data.models.sql_types import enum_column_type


class PalletMovement(Base):
    """Immutable warehouse movement history for a pallet."""

    __tablename__ = "pallet_movements"
    __table_args__ = (
        CheckConstraint(
            "from_location_id is not null or to_location_id is not null",
            name="movement_has_location",
        ),
        CheckConstraint(
            """
            from_location_id is null
            or to_location_id is null
            or from_location_id <> to_location_id
            or movement_type = 'CORRECTED'
            """,
            name="movement_location_change_or_corrected",
        ),
        Index("ix_pallet_movements_pallet_id_movement_timestamp", "pallet_id", "movement_timestamp"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    pallet_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pallets.id", ondelete="RESTRICT"),
        index=True,
    )
    from_location_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("warehouse_locations.id", ondelete="SET NULL"),
        index=True,
    )
    to_location_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("warehouse_locations.id", ondelete="SET NULL"),
        index=True,
    )
    movement_type: Mapped[PalletMovementType] = mapped_column(
        enum_column_type(PalletMovementType, "pallet_movement_type"),
        index=True,
    )
    movement_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    performed_by: Mapped[str | None] = mapped_column(String(100))
    remarks: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pallet: Mapped["Pallet"] = relationship(back_populates="pallet_movements")
    from_location: Mapped["WarehouseLocation | None"] = relationship(
        back_populates="movements_from_here",
        foreign_keys=[from_location_id],
    )
    to_location: Mapped["WarehouseLocation | None"] = relationship(
        back_populates="movements_to_here",
        foreign_keys=[to_location_id],
    )
