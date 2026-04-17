"""Delivery slip business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from logistics_app.application.services.application_logging_service import (
    ApplicationLogContext,
    ApplicationLoggingService,
)
from logistics_app.application.services.audit_trail_service import AuditContext, AuditTrailService
from logistics_app.data.models.delivery_slip import DeliverySlip
from logistics_app.data.models.enums import DeliverySlipStatus, PalletStatus, AuditActionType, AuditEntityType
from logistics_app.infrastructure.config.settings import ApplicationSettings, get_settings

if TYPE_CHECKING:
    from logistics_app.data.models.pallet import Pallet


class DeliverySlipWorkflowError(Exception):
    """Raised when a delivery slip transition violates business rules."""


class DeliverySlipService:
    """Orchestrates delivery slip lifecycle transitions."""

    def __init__(
        self,
        session: Session,
        settings: ApplicationSettings | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._audit_trail_service = AuditTrailService(session)
        self._application_logging_service = ApplicationLoggingService(
            session=session,
            settings=self._settings,
        )

    def release_for_loading(
        self,
        delivery_slip_id: int,
        performed_by: str | None,
        source_system: str | None,
    ) -> DeliverySlip:
        """Transport releases the delivery for warehouse loading.

        Requires all transport-defined document types to be AVAILABLE.
        """
        delivery = self._get_delivery(delivery_slip_id)

        self._verify_document_completeness(delivery)

        old_status = delivery.status
        delivery.status = DeliverySlipStatus.RELEASED_BY_TRANSPORT
        delivery.updated_at = datetime.now(UTC)
        delivery.updated_by = performed_by

        self._audit_trail_service.record_status_changed(
            entity_type=AuditEntityType.DELIVERY_SLIP,
            entity_id=delivery_slip_id,
            previous_status=old_status,
            new_status=delivery.status,
            context=AuditContext(
                performed_by=performed_by,
                source_system=source_system,
                delivery_slip_id=delivery_slip_id,
            ),
        )
        return delivery

    def mark_loading_in_progress(
        self,
        delivery_slip_id: int,
        performed_by: str | None,
        source_system: str | None,
    ) -> DeliverySlip:
        """Warehouse starts the loading process."""
        delivery = self._get_delivery(delivery_slip_id)
        if delivery.status not in {DeliverySlipStatus.RELEASED_BY_TRANSPORT, DeliverySlipStatus.READY_TO_LOAD}:
             raise DeliverySlipWorkflowError(f"Cannot start loading from status {delivery.status}")

        old_status = delivery.status
        delivery.status = DeliverySlipStatus.LOADING_IN_PROGRESS
        delivery.updated_at = datetime.now(UTC)
        delivery.updated_by = performed_by

        self._session.flush()
        return delivery

    def check_loading_completeness(self, delivery_slip_id: int) -> dict[str, Any]:
        """Check if all pallets for the delivery are loaded."""
        delivery = self._get_delivery(delivery_slip_id)
        return self._check_loading_completeness_internal(delivery)

    def finalize_shipment(
        self,
        delivery_slip_id: int,
        performed_by: str | None,
        source_system: str | None,
    ) -> DeliverySlip:
        """Complete the loading and mark the delivery as Shipped."""
        delivery = self._get_delivery(delivery_slip_id)
        completeness = self._check_loading_completeness_internal(delivery)

        if not completeness["is_complete"]:
             raise DeliverySlipWorkflowError(
                 f"Cannot finalize shipment: {completeness['remaining']} pallets are still not loaded."
             )

        old_status = delivery.status
        delivery.status = DeliverySlipStatus.SHIPPED
        delivery.updated_at = datetime.now(UTC)
        delivery.updated_by = performed_by

        self._audit_trail_service.record_status_changed(
            entity_type=AuditEntityType.DELIVERY_SLIP,
            entity_id=delivery_slip_id,
            previous_status=old_status,
            new_status=delivery.status,
            context=AuditContext(
                performed_by=performed_by,
                source_system=source_system,
                delivery_slip_id=delivery_slip_id,
            ),
        )

        # Automatically transition to SIGNED_CMR_PENDING as that's the next logical state
        delivery.status = DeliverySlipStatus.SIGNED_CMR_PENDING

        return delivery

    def _get_delivery(self, delivery_slip_id: int) -> DeliverySlip:
        delivery = self._session.get(DeliverySlip, delivery_slip_id)
        if not delivery:
            raise DeliverySlipWorkflowError(f"Delivery slip {delivery_slip_id} not found.")
        return delivery

    def _verify_document_completeness(self, delivery: DeliverySlip) -> None:
        """Check if all mandatory document types have at least one AVAILABLE version."""
        from logistics_app.data.models.enums import DocumentStatus

        # Find mandatory document types from print instructions or business rules
        mandatory_types = {
            instr.document_type for instr in delivery.document_print_instructions
            if instr.is_mandatory
        }

        # Check current available documents
        available_types = {
            doc.document_type for doc in delivery.documents
            if doc.document_status == DocumentStatus.AVAILABLE and doc.is_latest_version
        }

        missing = mandatory_types - available_types
        if missing:
            missing_names = ", ".join(m.value for m in missing)
            raise DeliverySlipWorkflowError(
                f"Cannot release: Missing required documents: {missing_names}"
            )

    def _check_loading_completeness_internal(self, delivery: DeliverySlip) -> dict[str, Any]:
        total_pallets = len(delivery.pallets)
        loaded_pallets = sum(1 for p in delivery.pallets if p.status == PalletStatus.LOADED)
        return {
            "total": total_pallets,
            "loaded": loaded_pallets,
            "remaining": total_pallets - loaded_pallets,
            "is_complete": total_pallets > 0 and total_pallets == loaded_pallets
        }
