"""Pallet API schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from logistics_app.data.models.enums import PalletMovementType, PalletStatus
from logistics_app.service_api.schemas.common import OrmResponseModel


class PalletResponse(OrmResponseModel):
    id: int
    delivery_slip_id: int
    pallet_identifier: str
    split_transport_id: int | None
    current_warehouse_location_id: int | None
    status: PalletStatus
    gross_weight_kg: Decimal | None
    package_count: int | None
    description: str | None
    loaded_at: datetime | None
    delivered_at: datetime | None
    updated_at: datetime


class PalletUpdateRequest(BaseModel):
    delivery_slip_id: int | None = None
    split_transport_id: int | None = None
    current_warehouse_location_id: int | None = None
    status: PalletStatus | None = None
    gross_weight_kg: Decimal | None = None
    package_count: int | None = None
    description: str | None = None
    acting_user: str | None = None
    source_system: str | None = None


class PalletMovementRequest(BaseModel):
    to_location_id: int
    movement_type: PalletMovementType = PalletMovementType.RELOCATED
    remarks: str | None = None
    performed_by: str | None = None
    source_system: str | None = None


class PalletMovementResponse(OrmResponseModel):
    id: int
    pallet_id: int
    from_location_id: int | None
    to_location_id: int | None
    movement_type: PalletMovementType
    movement_timestamp: datetime
    performed_by: str | None
    remarks: str | None


class PalletLoadedRequest(BaseModel):
    acting_user: str | None = None
    source_system: str | None = None
