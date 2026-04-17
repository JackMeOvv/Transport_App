"""Warehouse location repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from logistics_app.data.models.warehouse_location import WarehouseLocation


class WarehouseLocationRepository:
    """Explicit repository for warehouse locations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, warehouse_location_id: int) -> WarehouseLocation | None:
        """Load one warehouse location by primary key."""
        return self._session.get(WarehouseLocation, warehouse_location_id)

    def get_by_code(self, location_code: str) -> WarehouseLocation | None:
        """Load one warehouse location by business code."""
        statement = (
            select(WarehouseLocation)
            .where(WarehouseLocation.location_code == location_code)
            .limit(1)
        )
        return self._session.scalar(statement)
