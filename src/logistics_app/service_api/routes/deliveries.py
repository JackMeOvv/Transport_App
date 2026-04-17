"""Delivery slip routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from logistics_app.application.services import DeliverySlipService
from logistics_app.service_api.dependencies import get_db_session
from logistics_app.service_api.errors import raise_http_error_for_exception
from logistics_app.service_api.schemas.deliveries import (
    DeliverySlipDetailResponse,
    DeliverySlipSummaryResponse,
    DeliverySlipUpdateRequest,
)

router = APIRouter(prefix="/delivery-slips", tags=["delivery-slips"])


@router.get("", response_model=list[DeliverySlipSummaryResponse])
def list_delivery_slips(
    delivery_slip_number: str | None = Query(default=None),
    session: Session = Depends(get_db_session),
) -> list[DeliverySlipSummaryResponse]:
    """Return open delivery slips or one delivery slip by business number."""
    service = DeliverySlipService(session)
    try:
        if delivery_slip_number:
            return [DeliverySlipSummaryResponse.model_validate(service.get_delivery_slip_by_number(delivery_slip_number))]
        return [
            DeliverySlipSummaryResponse.model_validate(delivery_slip)
            for delivery_slip in service.list_open_delivery_slips()
        ]
    except Exception as exception:
        raise_http_error_for_exception(exception)


@router.get("/{delivery_slip_id}", response_model=DeliverySlipDetailResponse)
def get_delivery_slip(
    delivery_slip_id: int,
    session: Session = Depends(get_db_session),
) -> DeliverySlipDetailResponse:
    """Return one delivery slip."""
    service = DeliverySlipService(session)
    try:
        return DeliverySlipDetailResponse.model_validate(service.get_delivery_slip(delivery_slip_id))
    except Exception as exception:
        raise_http_error_for_exception(exception)


@router.put("/{delivery_slip_id}", response_model=DeliverySlipDetailResponse)
def update_delivery_slip(
    delivery_slip_id: int,
    request: DeliverySlipUpdateRequest,
    session: Session = Depends(get_db_session),
) -> DeliverySlipDetailResponse:
    """Update a delivery slip through the service layer."""
    service = DeliverySlipService(session)
    updates = request.model_dump(exclude={"changed_by", "source_system"}, exclude_none=True)
    try:
        delivery_slip = service.update_delivery_slip(
            delivery_slip_id=delivery_slip_id,
            updates=updates,
            changed_by=request.changed_by,
            source_system=request.source_system,
        )
        return DeliverySlipDetailResponse.model_validate(delivery_slip)
    except Exception as exception:
        raise_http_error_for_exception(exception)
