"""Pallet and warehouse movement routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from logistics_app.application.services import PalletMovementService, PalletService
from logistics_app.service_api.dependencies import get_db_session
from logistics_app.service_api.errors import raise_http_error_for_exception
from logistics_app.service_api.schemas.pallets import (
    PalletLoadedRequest,
    PalletMovementRequest,
    PalletMovementResponse,
    PalletResponse,
    PalletUpdateRequest,
)

router = APIRouter(tags=["pallets"])


@router.get("/pallets/{pallet_id}", response_model=PalletResponse)
def get_pallet(
    pallet_id: int,
    session: Session = Depends(get_db_session),
) -> PalletResponse:
    """Return one pallet by primary key."""
    service = PalletService(session)
    try:
        return PalletResponse.model_validate(service.get_pallet(pallet_id))
    except Exception as exception:
        raise_http_error_for_exception(exception)


@router.get("/pallets/by-identifier/{pallet_identifier}", response_model=PalletResponse)
def get_pallet_by_identifier(
    pallet_identifier: str,
    session: Session = Depends(get_db_session),
) -> PalletResponse:
    """Return one pallet by business identifier."""
    service = PalletService(session)
    try:
        return PalletResponse.model_validate(service.get_pallet_by_identifier(pallet_identifier))
    except Exception as exception:
        raise_http_error_for_exception(exception)


@router.get("/delivery-slips/{delivery_slip_id}/pallets", response_model=list[PalletResponse])
def list_delivery_pallets(
    delivery_slip_id: int,
    session: Session = Depends(get_db_session),
) -> list[PalletResponse]:
    """Return pallets linked to a delivery slip."""
    service = PalletService(session)
    return [
        PalletResponse.model_validate(pallet)
        for pallet in service.list_pallets_by_delivery_slip(delivery_slip_id)
    ]


@router.put("/pallets/{pallet_id}", response_model=PalletResponse)
def update_pallet(
    pallet_id: int,
    request: PalletUpdateRequest,
    session: Session = Depends(get_db_session),
) -> PalletResponse:
    """Update pallet metadata through the service layer."""
    service = PalletService(session)
    try:
        pallet = service.update_pallet(
            pallet_id=pallet_id,
            updates=request.model_dump(exclude={"acting_user", "source_system"}, exclude_none=True),
            acting_user=request.acting_user,
            source_system=request.source_system,
        )
        return PalletResponse.model_validate(pallet)
    except Exception as exception:
        raise_http_error_for_exception(exception)


@router.post("/pallets/{pallet_id}/movements", response_model=PalletMovementResponse)
def move_pallet(
    pallet_id: int,
    request: PalletMovementRequest,
    session: Session = Depends(get_db_session),
) -> PalletMovementResponse:
    """Record a pallet movement and update current warehouse location."""
    service = PalletMovementService(session)
    try:
        movement = service.move_pallet(
            pallet_id=pallet_id,
            to_location_id=request.to_location_id,
            performed_by=request.performed_by,
            source_system=request.source_system,
            movement_type=request.movement_type,
            remarks=request.remarks,
        )
        return PalletMovementResponse.model_validate(movement)
    except Exception as exception:
        raise_http_error_for_exception(exception)


@router.post("/pallets/{pallet_id}/mark-loaded", response_model=PalletResponse)
def mark_pallet_loaded(
    pallet_id: int,
    request: PalletLoadedRequest,
    session: Session = Depends(get_db_session),
) -> PalletResponse:
    """Mark one pallet as loaded."""
    service = PalletService(session)
    try:
        pallet = service.mark_pallet_loaded(
            pallet_id=pallet_id,
            acting_user=request.acting_user,
            source_system=request.source_system,
        )
        return PalletResponse.model_validate(pallet)
    except Exception as exception:
        raise_http_error_for_exception(exception)
