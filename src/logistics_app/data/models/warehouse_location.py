"""Warehouse location ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from logistics_app.data.models.base import Base
from logistics_app.data.models.enums import WarehouseLocationType
from logistics_app.data.models.sql_types import enum_column_type


class WarehouseLocation(Base):
    """A physical warehouse position used for storage, staging, or loading."""

    __tablename__ = "warehouse_locations"
    __table_args__ = (
        CheckConstraint("char_length(trim(location_code)) > 0", name="location_code_not_blank"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    location_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    location_name: Mapped[str | None] = mapped_column(String(100))
    location_type: Mapped[WarehouseLocationType] = mapped_column(
        enum_column_type(WarehouseLocationType, "warehouse_location_type"),
        index=True,
    )
    zone_code: Mapped[str | None] = mapped_column(String(50), index=True)
    aisle: Mapped[str | None] = mapped_column(String(20))
    rack: Mapped[str | None] = mapped_column(String(20))
    level: Mapped[str | None] = mapped_column(String(20))
    position: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pallets: Mapped[list["Pallet"]] = relationship(back_populates="current_warehouse_location")
    movements_from_here: Mapped[list["PalletMovement"]] = relationship(
        back_populates="from_location",
        foreign_keys="PalletMovement.from_location_id",
    )
    movements_to_here: Mapped[list["PalletMovement"]] = relationship(
        back_populates="to_location",
        foreign_keys="PalletMovement.to_location_id",
    )
