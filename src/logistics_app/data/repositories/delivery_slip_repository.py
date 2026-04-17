"""Delivery slip repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from logistics_app.data.models.delivery_slip import DeliverySlip
from logistics_app.data.models.enums import DeliverySlipStatus


class DeliverySlipRepository:
    """Explicit repository for delivery slip reads and writes."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, delivery_slip: DeliverySlip) -> DeliverySlip:
        """Add a delivery slip to the current unit of work."""
        self._session.add(delivery_slip)
        return delivery_slip

    def get_by_id(self, delivery_slip_id: int) -> DeliverySlip | None:
        """Load one delivery slip by primary key."""
        return self._session.get(DeliverySlip, delivery_slip_id)

    def get_by_number(self, delivery_slip_number: str) -> DeliverySlip | None:
        """Load one delivery slip by business number."""
        statement = (
            select(DeliverySlip)
            .where(DeliverySlip.delivery_slip_number == delivery_slip_number)
            .limit(1)
        )
        return self._session.scalar(statement)

    def list_open(self) -> list[DeliverySlip]:
        """Return delivery slips that remain in the active operational flow."""
        statement = (
            select(DeliverySlip)
            .where(
                DeliverySlip.status.notin_(
                    [DeliverySlipStatus.DELIVERED, DeliverySlipStatus.CANCELLED]
                )
            )
            .order_by(DeliverySlip.delivery_date, DeliverySlip.delivery_slip_number)
        )
        return list(self._session.scalars(statement))
