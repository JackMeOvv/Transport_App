"""Pallet movement repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from logistics_app.data.models.pallet_movement import PalletMovement


class PalletMovementRepository:
    """Explicit repository for pallet movement history."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, pallet_movement: PalletMovement) -> PalletMovement:
        """Add a pallet movement to the current unit of work."""
        self._session.add(pallet_movement)
        return pallet_movement

    def list_by_pallet(self, pallet_id: int) -> list[PalletMovement]:
        """Return movement history ordered by movement timestamp."""
        statement = (
            select(PalletMovement)
            .where(PalletMovement.pallet_id == pallet_id)
            .order_by(PalletMovement.movement_timestamp.desc(), PalletMovement.id.desc())
        )
        return list(self._session.scalars(statement))
