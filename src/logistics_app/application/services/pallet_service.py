"""Pallet application service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from logistics_app.application.services.audit_trail_service import AuditContext, AuditTrailService
from logistics_app.application.services.service_errors import (
    ResourceNotFoundError,
    ServiceValidationError,
)
from logistics_app.data.models.enums import AuditEntityType, PalletStatus
from logistics_app.data.models.pallet import Pallet
from logistics_app.data.repositories.delivery_slip_repository import DeliverySlipRepository
from logistics_app.data.repositories.pallet_repository import PalletRepository
from logistics_app.data.repositories.warehouse_location_repository import WarehouseLocationRepository


class PalletService:
    """Provides pallet retrieval and update use cases."""

    def __init__(self, session: Session) -> None:
        self._delivery_repository = DeliverySlipRepository(session)
        self._pallet_repository = PalletRepository(session)
        self._warehouse_location_repository = WarehouseLocationRepository(session)
        self._audit_trail_service = AuditTrailService(session)

    def get_pallet(self, pallet_id: int) -> Pallet:
        """Return one pallet by primary key."""
        pallet = self._pallet_repository.get_by_id(pallet_id)
        if pallet is None:
            raise ResourceNotFoundError(f"Pallet {pallet_id} was not found.")
        return pallet

    def get_pallet_by_identifier(self, pallet_identifier: str) -> Pallet:
        """Return one pallet by business identifier."""
        pallet = self._pallet_repository.get_by_identifier(pallet_identifier)
        if pallet is None:
            raise ResourceNotFoundError(f"Pallet '{pallet_identifier}' was not found.")
        return pallet

    def list_pallets_by_delivery_slip(self, delivery_slip_id: int) -> list[Pallet]:
        """Return pallets linked to a delivery slip."""
        return self._pallet_repository.list_by_delivery_slip(delivery_slip_id)

    def update_pallet(
        self,
        pallet_id: int,
        updates: dict[str, Any],
        acting_user: str | None,
        source_system: str | None,
    ) -> Pallet:
        """Apply explicit field updates to a pallet."""
        pallet = self.get_pallet(pallet_id)
        self._validate_reference_updates(updates)

        changed_fields: list[str] = []
        previous_status = pallet.status
        previous_delivery_slip_id = pallet.delivery_slip_id

        for field_name, new_value in updates.items():
            if not hasattr(pallet, field_name):
                continue
            if getattr(pallet, field_name) == new_value:
                continue
            setattr(pallet, field_name, new_value)
            changed_fields.append(field_name)

        if not changed_fields:
            return pallet

        pallet.updated_at = datetime.now(UTC)
        pallet.updated_by = acting_user

        audit_context = AuditContext(
            performed_by=acting_user,
            source_system=source_system,
            delivery_slip_id=pallet.delivery_slip_id,
            pallet_id=pallet.id,
            split_transport_id=pallet.split_transport_id,
        )
        if "delivery_slip_id" in changed_fields and pallet.delivery_slip_id != previous_delivery_slip_id:
            self._audit_trail_service.record_pallet_assigned(
                pallet_id=pallet.id,
                assigned_delivery_slip_id=pallet.delivery_slip_id,
                context=audit_context,
            )
        if "status" in changed_fields:
            self._audit_trail_service.record_status_changed(
                entity_type=AuditEntityType.PALLET,
                entity_id=pallet.id,
                previous_status=previous_status.value if previous_status is not None else None,
                new_status=pallet.status.value,
                context=audit_context,
            )
        return pallet

    def mark_pallet_loaded(
        self,
        pallet_id: int,
        acting_user: str | None,
        source_system: str | None,
    ) -> Pallet:
        """Mark a pallet as loaded and create the related audit trail."""
        pallet = self.get_pallet(pallet_id)
        previous_status = pallet.status

        pallet.status = PalletStatus.LOADED
        pallet.loaded_at = datetime.now(UTC)
        pallet.updated_at = pallet.loaded_at
        pallet.updated_by = acting_user

        audit_context = AuditContext(
            performed_by=acting_user,
            source_system=source_system,
            delivery_slip_id=pallet.delivery_slip_id,
            pallet_id=pallet.id,
            split_transport_id=pallet.split_transport_id,
        )
        self._audit_trail_service.record_pallet_loaded(
            pallet_id=pallet.id,
            context=audit_context,
        )
        if previous_status != pallet.status:
            self._audit_trail_service.record_status_changed(
                entity_type=AuditEntityType.PALLET,
                entity_id=pallet.id,
                previous_status=previous_status.value if previous_status is not None else None,
                new_status=pallet.status.value,
                context=audit_context,
            )
        return pallet

    def _validate_reference_updates(self, updates: dict[str, Any]) -> None:
        delivery_slip_id = updates.get("delivery_slip_id")
        if delivery_slip_id is not None and self._delivery_repository.get_by_id(delivery_slip_id) is None:
            raise ServiceValidationError(f"Delivery slip {delivery_slip_id} was not found.")

        location_id = updates.get("current_warehouse_location_id")
        if (
            location_id is not None
            and self._warehouse_location_repository.get_by_id(location_id) is None
        ):
            raise ServiceValidationError(f"Warehouse location {location_id} was not found.")
