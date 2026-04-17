"""Delivery API schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from logistics_app.data.models.enums import DeliverySlipStatus
from logistics_app.service_api.schemas.common import OrmResponseModel


class DeliverySlipSummaryResponse(OrmResponseModel):
    id: int
    delivery_slip_number: str
    customer_reference: str | None
    customer_name: str | None
    delivery_date: date | None
    destination_name: str | None
    transport_reference: str | None
    status: DeliverySlipStatus
    is_split_transport: bool
    updated_at: datetime


class DeliverySlipDetailResponse(DeliverySlipSummaryResponse):
    origin_name: str | None
    notes: str | None
    created_by: str | None
    updated_by: str | None


class DeliverySlipUpdateRequest(BaseModel):
    customer_reference: str | None = None
    customer_name: str | None = None
    delivery_date: date | None = None
    origin_name: str | None = None
    destination_name: str | None = None
    transport_reference: str | None = None
    status: DeliverySlipStatus | None = None
    is_split_transport: bool | None = None
    notes: str | None = None
    changed_by: str | None = None
    source_system: str | None = None
