"""Unit tests for pallet workflow services."""

from __future__ import annotations

from dataclasses import dataclass, field

from logistics_app.application.services.pallet_movement_service import PalletMovementService
from logistics_app.application.services.pallet_service import PalletService
from logistics_app.data.models.delivery_slip import DeliverySlip
from logistics_app.data.models.enums import (
    DeliverySlipStatus,
    PalletMovementType,
    PalletStatus,
    WarehouseLocationType,
)
from logistics_app.data.models.pallet import Pallet
from logistics_app.data.models.warehouse_location import WarehouseLocation


@dataclass
class FakeDeliverySlipRepository:
    """Minimal delivery repository for pallet service tests."""

    delivery_slips: dict[int, DeliverySlip]

    def get_by_id(self, delivery_slip_id: int) -> DeliverySlip | None:
        return self.delivery_slips.get(delivery_slip_id)


@dataclass
class FakePalletRepository:
    """Minimal pallet repository for workflow tests."""

    pallets: dict[int, Pallet]

    def get_by_id(self, pallet_id: int) -> Pallet | None:
        return self.pallets.get(pallet_id)

    def get_by_identifier(self, pallet_identifier: str) -> Pallet | None:
        for pallet in self.pallets.values():
            if pallet.pallet_identifier == pallet_identifier:
                return pallet
        return None

    def list_by_delivery_slip(self, delivery_slip_id: int) -> list[Pallet]:
        return [
            pallet for pallet in self.pallets.values() if pallet.delivery_slip_id == delivery_slip_id
        ]


@dataclass
class FakeWarehouseLocationRepository:
    """Minimal warehouse location repository for movement tests."""

    locations: dict[int, WarehouseLocation]

    def get_by_id(self, warehouse_location_id: int) -> WarehouseLocation | None:
        return self.locations.get(warehouse_location_id)


@dataclass
class FakePalletMovementRepository:
    """Minimal pallet movement repository for movement tests."""

    movements: list[object] = field(default_factory=list)

    def add(self, pallet_movement: object) -> object:
        self.movements.append(pallet_movement)
        return pallet_movement

    def list_by_pallet(self, pallet_id: int) -> list[object]:
        return [movement for movement in self.movements if movement.pallet_id == pallet_id]


@dataclass
class FakeAuditTrailService:
    """Captures pallet-related audit actions for assertions."""

    pallet_loaded_calls: list[dict[str, object]] = field(default_factory=list)
    status_change_calls: list[dict[str, object]] = field(default_factory=list)
    pallet_moved_calls: list[dict[str, object]] = field(default_factory=list)
    pallet_assigned_calls: list[dict[str, object]] = field(default_factory=list)

    def record_pallet_loaded(self, pallet_id: int, context: object) -> None:
        self.pallet_loaded_calls.append({"pallet_id": pallet_id, "context": context})

    def record_status_changed(
        self,
        entity_type: object,
        entity_id: int,
        previous_status: str | None,
        new_status: str,
        context: object,
    ) -> None:
        self.status_change_calls.append(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "previous_status": previous_status,
                "new_status": new_status,
                "context": context,
            }
        )

    def record_pallet_moved(
        self,
        pallet_id: int,
        from_location_code: str | None,
        to_location_code: str | None,
        context: object,
    ) -> None:
        self.pallet_moved_calls.append(
            {
                "pallet_id": pallet_id,
                "from_location_code": from_location_code,
                "to_location_code": to_location_code,
                "context": context,
            }
        )

    def record_pallet_assigned(
        self,
        pallet_id: int,
        assigned_delivery_slip_id: int,
        context: object,
    ) -> None:
        self.pallet_assigned_calls.append(
            {
                "pallet_id": pallet_id,
                "assigned_delivery_slip_id": assigned_delivery_slip_id,
                "context": context,
            }
        )


class FakeSession:
    """Placeholder session for constructing services."""


def test_mark_pallet_loaded_updates_status_and_records_audit_entries() -> None:
    """Loading a pallet should update the state and create explicit audit records."""
    pallet = Pallet(
        id=10,
        delivery_slip_id=100,
        pallet_identifier="PALLET-10",
        status=PalletStatus.STAGED,
    )
    service = PalletService(session=FakeSession())
    fake_audit_service = FakeAuditTrailService()
    service._pallet_repository = FakePalletRepository({10: pallet})
    service._delivery_repository = FakeDeliverySlipRepository(
        {
            100: DeliverySlip(
                id=100,
                delivery_slip_number="DEL-2026-0100",
                status=DeliverySlipStatus.READY_TO_LOAD,
            )
        }
    )
    service._warehouse_location_repository = FakeWarehouseLocationRepository({})
    service._audit_trail_service = fake_audit_service

    updated_pallet = service.mark_pallet_loaded(
        pallet_id=10,
        acting_user="warehouse.user",
        source_system="desktop_client",
    )

    assert updated_pallet.status == PalletStatus.LOADED
    assert updated_pallet.loaded_at is not None
    assert updated_pallet.updated_by == "warehouse.user"
    assert fake_audit_service.pallet_loaded_calls[0]["pallet_id"] == 10
    assert fake_audit_service.status_change_calls[0]["previous_status"] == "STAGED"
    assert fake_audit_service.status_change_calls[0]["new_status"] == "LOADED"


def test_move_pallet_updates_location_status_and_logs_split_transport_context() -> None:
    """Pallet movement should update the pallet and keep rare split transport context intact."""
    from_location = WarehouseLocation(
        id=1,
        location_code="A-01-01",
        location_type=WarehouseLocationType.STORAGE,
    )
    to_location = WarehouseLocation(
        id=2,
        location_code="STAGE-01",
        location_type=WarehouseLocationType.STAGING,
    )
    pallet = Pallet(
        id=20,
        delivery_slip_id=200,
        pallet_identifier="PALLET-20",
        split_transport_id=777,
        current_warehouse_location_id=1,
        status=PalletStatus.IN_WAREHOUSE,
    )
    pallet.current_warehouse_location = from_location

    service = PalletMovementService(session=FakeSession())
    fake_movement_repository = FakePalletMovementRepository()
    fake_audit_service = FakeAuditTrailService()
    service._movement_repository = fake_movement_repository
    service._pallet_repository = FakePalletRepository({20: pallet})
    service._warehouse_location_repository = FakeWarehouseLocationRepository(
        {1: from_location, 2: to_location}
    )
    service._audit_trail_service = fake_audit_service

    movement = service.move_pallet(
        pallet_id=20,
        to_location_id=2,
        performed_by="warehouse.user",
        source_system="desktop_client",
        movement_type=PalletMovementType.STAGED_FOR_LOADING,
        remarks="Move to loading stage",
    )

    assert movement.from_location_id == 1
    assert movement.to_location_id == 2
    assert pallet.current_warehouse_location_id == 2
    assert pallet.status == PalletStatus.STAGED
    assert fake_movement_repository.movements[0] is movement
    assert fake_audit_service.pallet_moved_calls[0]["from_location_code"] == "A-01-01"
    assert fake_audit_service.pallet_moved_calls[0]["to_location_code"] == "STAGE-01"
    assert fake_audit_service.pallet_moved_calls[0]["context"].split_transport_id == 777
    assert fake_audit_service.status_change_calls[0]["new_status"] == "STAGED"
