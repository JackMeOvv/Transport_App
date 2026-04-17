"""Audit API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from logistics_app.data.models.enums import AuditActionType, AuditEntityType
from logistics_app.service_api.schemas.common import OrmResponseModel


class AuditLogWriteRequest(BaseModel):
    entity_type: AuditEntityType
    entity_id: int | None = None
    action_type: AuditActionType
    performed_by: str | None = None
    source_system: str | None = None
    delivery_slip_id: int | None = None
    pallet_id: int | None = None
    document_id: int | None = None
    split_transport_id: int | None = None
    details: dict[str, Any]


class AuditLogResponse(OrmResponseModel):
    id: int
    occurred_at: datetime
    entity_type: AuditEntityType
    entity_id: int | None
    action_type: AuditActionType
    delivery_slip_id: int | None
    pallet_id: int | None
    document_id: int | None
    split_transport_id: int | None
    performed_by: str | None
    source_system: str | None
    details_json: dict[str, Any] | list[Any] | None
