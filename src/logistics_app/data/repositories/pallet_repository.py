"""Pallet repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from logistics_app.data.models.pallet import Pallet


class PalletRepository:
    """Explicit repository for pallet records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, pallet: Pallet) -> Pallet:
        """Add a pallet to the current unit of work."""
        self._session.add(pallet)
        return pallet

    def get_by_id(self, pallet_id: int) -> Pallet | None:
        """Load one pallet by primary key."""
        return self._session.get(Pallet, pallet_id)

    def get_by_identifier(self, pallet_identifier: str) -> Pallet | None:
        """Load one pallet by business identifier."""
        statement = select(Pallet).where(Pallet.pallet_identifier == pallet_identifier).limit(1)
        return self._session.scalar(statement)

    def list_by_delivery_slip(self, delivery_slip_id: int) -> list[Pallet]:
        """Return all pallets linked to one delivery slip."""
        statement = (
            select(Pallet)
            .where(Pallet.delivery_slip_id == delivery_slip_id)
            .order_by(Pallet.pallet_identifier)
        )
        return list(self._session.scalars(statement))
