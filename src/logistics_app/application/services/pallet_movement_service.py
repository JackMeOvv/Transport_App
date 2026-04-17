"""Pallet movement application service."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from logistics_app.application.services.audit_trail_service import AuditContext, AuditTrailService
from logistics_app.application.services.service_errors import (
    ResourceNotFoundError,
    ServiceValidationError,
)
from logistics_app.data.models.enums import AuditEntityType, PalletMovementType, PalletStatus
from logistics_app.data.models.pallet_movement import PalletMovement
from logistics_app.data.repositories.pallet_movement_repository import PalletMovementRepository
from logistics_app.data.repositories.pallet_repository import PalletRepository
from logistics_app.data.repositories.warehouse_location_repository import WarehouseLocationRepository


class PalletMovementService:
    """Handles pallet movement recording and current location updates."""

    def __init__(self, session: Session) -> None:
        self._movement_repository = PalletMovementRepository(session)
        self._pallet_repository = PalletRepository(session)
        self._warehouse_location_repository = WarehouseLocationRepository(session)
        self._audit_trail_service = AuditTrailService(session)

    def list_movements_for_pallet(self, pallet_id: int) -> list[PalletMovement]:
        """Return pallet movement history."""
        return self._movement_repository.list_by_pallet(pallet_id)

    def move_pallet(
        self,
        pallet_id: int,
        to_location_id: int,
        performed_by: str | None,
        source_system: str | None,
        movement_type: PalletMovementType = PalletMovementType.RELOCATED,
        remarks: str | None = None,
    ) -> PalletMovement:
        """Move a pallet to another warehouse location and update current state."""
        pallet = self._pallet_repository.get_by_id(pallet_id)
        if pallet is None:
            raise ResourceNotFoundError(f"Pallet {pallet_id} was not found.")

        to_location = self._warehouse_location_repository.get_by_id(to_location_id)
        if to_location is None:
            raise ServiceValidationError(f"Warehouse location {to_location_id} was not found.")

        from_location = pallet.current_warehouse_location
        if from_location is not None and from_location.id == to_location.id:
            raise ServiceValidationError(
                "The destination warehouse location must differ from the current location."
            )

        movement_timestamp = datetime.now(UTC)
        movement = PalletMovement(
            pallet_id=pallet.id,
            from_location_id=from_location.id if from_location is not None else None,
            to_location_id=to_location.id,
            movement_type=movement_type,
            movement_timestamp=movement_timestamp,
            performed_by=performed_by,
            remarks=remarks,
        )
        self._movement_repository.add(movement)

        previous_status = pallet.status
        pallet.current_warehouse_location_id = to_location.id
        pallet.updated_at = movement_timestamp
        pallet.updated_by = performed_by
        pallet.status = self._derive_status_after_move(
            current_status=pallet.status,
            movement_type=movement_type,
            destination_location_type=to_location.location_type.value,
        )

        audit_context = AuditContext(
            performed_by=performed_by,
            source_system=source_system,
            delivery_slip_id=pallet.delivery_slip_id,
            pallet_id=pallet.id,
            split_transport_id=pallet.split_transport_id,
        )
        self._audit_trail_service.record_pallet_moved(
            pallet_id=pallet.id,
            from_location_code=from_location.location_code if from_location is not None else None,
            to_location_code=to_location.location_code,
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
        return movement

    def _derive_status_after_move(
        self,
        current_status: PalletStatus,
        movement_type: PalletMovementType,
        destination_location_type: str,
    ) -> PalletStatus:
        if movement_type == PalletMovementType.LOADED:
            return PalletStatus.LOADED
        if movement_type == PalletMovementType.STAGED_FOR_LOADING:
            return PalletStatus.STAGED
        if destination_location_type in {"STAGING", "LOADING_DOCK", "OUTBOUND_BUFFER"}:
            return PalletStatus.STAGED
        if current_status in {PalletStatus.LOADED, PalletStatus.DISPATCHED, PalletStatus.DELIVERED}:
            return current_status
        return PalletStatus.IN_WAREHOUSE
