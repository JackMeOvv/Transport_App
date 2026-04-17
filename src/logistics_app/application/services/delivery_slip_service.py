"""Delivery slip application service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from logistics_app.application.services.audit_trail_service import AuditContext, AuditTrailService
from logistics_app.application.services.service_errors import ResourceNotFoundError
from logistics_app.data.models.delivery_slip import DeliverySlip
from logistics_app.data.models.enums import AuditEntityType
from logistics_app.data.repositories.delivery_slip_repository import DeliverySlipRepository


class DeliverySlipService:
    """Provides delivery slip retrieval and update use cases for the API layer."""

    def __init__(self, session: Session) -> None:
        self._repository = DeliverySlipRepository(session)
        self._audit_trail_service = AuditTrailService(session)

    def list_open_delivery_slips(self) -> list[DeliverySlip]:
        """Return active delivery slips for the standard daily workflow."""
        return self._repository.list_open()

    def get_delivery_slip(self, delivery_slip_id: int) -> DeliverySlip:
        """Return one delivery slip by primary key."""
        delivery_slip = self._repository.get_by_id(delivery_slip_id)
        if delivery_slip is None:
            raise ResourceNotFoundError(f"Delivery slip {delivery_slip_id} was not found.")
        return delivery_slip

    def get_delivery_slip_by_number(self, delivery_slip_number: str) -> DeliverySlip:
        """Return one delivery slip by business number."""
        delivery_slip = self._repository.get_by_number(delivery_slip_number)
        if delivery_slip is None:
            raise ResourceNotFoundError(
                f"Delivery slip '{delivery_slip_number}' was not found."
            )
        return delivery_slip

    def update_delivery_slip(
        self,
        delivery_slip_id: int,
        updates: dict[str, Any],
        changed_by: str | None,
        source_system: str | None,
    ) -> DeliverySlip:
        """Apply explicit field updates to a delivery slip."""
        delivery_slip = self.get_delivery_slip(delivery_slip_id)
        changed_fields: list[str] = []
        previous_status = delivery_slip.status

        for field_name, new_value in updates.items():
            if not hasattr(delivery_slip, field_name):
                continue
            if getattr(delivery_slip, field_name) == new_value:
                continue
            setattr(delivery_slip, field_name, new_value)
            changed_fields.append(field_name)

        if not changed_fields:
            return delivery_slip

        delivery_slip.updated_at = datetime.now(UTC)
        delivery_slip.updated_by = changed_by

        audit_context = AuditContext(
            performed_by=changed_by,
            source_system=source_system,
            delivery_slip_id=delivery_slip.id,
        )
        self._audit_trail_service.record_delivery_slip_changed(
            delivery_slip_id=delivery_slip.id,
            changed_fields=changed_fields,
            context=audit_context,
        )
        if "status" in changed_fields:
            self._audit_trail_service.record_status_changed(
                entity_type=AuditEntityType.DELIVERY_SLIP,
                entity_id=delivery_slip.id,
                previous_status=previous_status.value if previous_status is not None else None,
                new_status=delivery_slip.status.value,
                context=audit_context,
            )
        return delivery_slip
