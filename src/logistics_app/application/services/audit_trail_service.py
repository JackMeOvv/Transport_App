"""Business audit trail support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from logistics_app.data.models.audit_log import AuditLog
from logistics_app.data.models.enums import AuditActionType, AuditEntityType, DocumentType
from logistics_app.data.repositories.audit_log_repository import AuditLogRepository


@dataclass(frozen=True, slots=True)
class AuditContext:
    """Context carried with a business audit event."""

    performed_by: str | None = None
    source_system: str | None = None
    delivery_slip_id: int | None = None
    pallet_id: int | None = None
    document_id: int | None = None
    split_transport_id: int | None = None


class AuditTrailService:
    """Creates explicit audit records for business-critical actions.

    This service does not attach hidden ORM hooks or automatic event handlers.
    Application code should call these methods intentionally at the point where
    the business action is confirmed.
    """

    def __init__(self, session: Session) -> None:
        self._repository = AuditLogRepository(session)

    def record_delivery_slip_created(
        self,
        delivery_slip_id: int,
        delivery_slip_number: str,
        context: AuditContext,
    ) -> AuditLog:
        """Audit the creation of a delivery slip."""
        return self._record(
            entity_type=AuditEntityType.DELIVERY_SLIP,
            entity_id=delivery_slip_id,
            action_type=AuditActionType.CREATE,
            context=context,
            details={
                "event_name": "delivery_slip_created",
                "delivery_slip_number": delivery_slip_number,
            },
        )

    def record_delivery_slip_changed(
        self,
        delivery_slip_id: int,
        changed_fields: list[str],
        context: AuditContext,
    ) -> AuditLog:
        """Audit changes to delivery slip data."""
        return self._record(
            entity_type=AuditEntityType.DELIVERY_SLIP,
            entity_id=delivery_slip_id,
            action_type=AuditActionType.UPDATE,
            context=context,
            details={
                "event_name": "delivery_slip_changed",
                "changed_fields": changed_fields,
            },
        )

    def record_document_uploaded(
        self,
        document_id: int,
        document_type: DocumentType,
        version_number: int,
        context: AuditContext,
    ) -> AuditLog:
        """Audit a document upload, including original and signed CMR uploads."""
        event_name = "signed_cmr_uploaded" if document_type == DocumentType.SIGNED_CMR else "document_uploaded"
        return self._record(
            entity_type=AuditEntityType.DOCUMENT,
            entity_id=document_id,
            action_type=AuditActionType.UPLOAD,
            context=context,
            details={
                "event_name": event_name,
                "document_type": document_type.value,
                "version_number": version_number,
            },
        )

    def record_transport_document_readiness_confirmed(
        self,
        delivery_slip_id: int,
        ready_document_types: list[DocumentType],
        context: AuditContext,
    ) -> AuditLog:
        """Audit transport confirmation that document readiness is complete."""
        return self._record(
            entity_type=AuditEntityType.DELIVERY_SLIP,
            entity_id=delivery_slip_id,
            action_type=AuditActionType.STATUS_CHANGE,
            context=context,
            details={
                "event_name": "transport_document_readiness_confirmed",
                "ready_document_types": [document_type.value for document_type in ready_document_types],
            },
        )

    def record_pallet_assigned(
        self,
        pallet_id: int,
        assigned_delivery_slip_id: int,
        context: AuditContext,
    ) -> AuditLog:
        """Audit pallet assignment to a delivery."""
        return self._record(
            entity_type=AuditEntityType.PALLET,
            entity_id=pallet_id,
            action_type=AuditActionType.UPDATE,
            context=context,
            details={
                "event_name": "pallet_assigned",
                "assigned_delivery_slip_id": assigned_delivery_slip_id,
            },
        )

    def record_pallet_moved(
        self,
        pallet_id: int,
        from_location_code: str | None,
        to_location_code: str | None,
        context: AuditContext,
    ) -> AuditLog:
        """Audit a pallet movement inside the warehouse."""
        return self._record(
            entity_type=AuditEntityType.PALLET,
            entity_id=pallet_id,
            action_type=AuditActionType.MOVE,
            context=context,
            details={
                "event_name": "pallet_moved",
                "from_location_code": from_location_code,
                "to_location_code": to_location_code,
            },
        )

    def record_pallet_loaded(
        self,
        pallet_id: int,
        context: AuditContext,
    ) -> AuditLog:
        """Audit that a pallet was marked as loaded."""
        return self._record(
            entity_type=AuditEntityType.PALLET,
            entity_id=pallet_id,
            action_type=AuditActionType.LOAD,
            context=context,
            details={"event_name": "pallet_marked_loaded"},
        )

    def record_print_instruction_changed(
        self,
        delivery_slip_id: int,
        document_type: DocumentType,
        required_copy_count: int,
        printer_role: str | None,
        context: AuditContext,
    ) -> AuditLog:
        """Audit print instruction changes controlled by transport."""
        return self._record(
            entity_type=AuditEntityType.DELIVERY_SLIP,
            entity_id=delivery_slip_id,
            action_type=AuditActionType.UPDATE,
            context=context,
            details={
                "event_name": "print_instruction_changed",
                "document_type": document_type.value,
                "required_copy_count": required_copy_count,
                "printer_role": printer_role,
            },
        )

    def record_print_action_requested(
        self,
        print_job_id: int,
        printer_name: str,
        requested_copy_count: int,
        context: AuditContext,
        document_type: DocumentType | None = None,
        printer_role: str | None = None,
        is_reprint: bool = False,
        is_manual_printer_override: bool = False,
    ) -> AuditLog:
        """Audit a requested print action."""
        details: dict[str, Any] = {
            "event_name": "print_action_requested",
            "printer_name": printer_name,
            "requested_copy_count": requested_copy_count,
            "is_reprint": is_reprint,
            "is_manual_printer_override": is_manual_printer_override,
        }
        if document_type is not None:
            details["document_type"] = document_type.value
        if printer_role is not None:
            details["printer_role"] = printer_role
        return self._record(
            entity_type=AuditEntityType.PRINT_JOB,
            entity_id=print_job_id,
            action_type=AuditActionType.PRINT,
            context=context,
            details=details,
        )

    def record_status_changed(
        self,
        entity_type: AuditEntityType,
        entity_id: int,
        previous_status: str | None,
        new_status: str,
        context: AuditContext,
    ) -> AuditLog:
        """Audit a business status transition."""
        return self._record(
            entity_type=entity_type,
            entity_id=entity_id,
            action_type=AuditActionType.STATUS_CHANGE,
            context=context,
            details={
                "event_name": "status_changed",
                "previous_status": previous_status,
                "new_status": new_status,
            },
        )

    def record_custom_event(
        self,
        entity_type: AuditEntityType,
        entity_id: int | None,
        action_type: AuditActionType,
        context: AuditContext,
        details: dict[str, Any],
    ) -> AuditLog:
        """Write an explicit custom audit event from an application command."""
        return self._record(
            entity_type=entity_type,
            entity_id=entity_id,
            action_type=action_type,
            context=context,
            details=details,
        )

    def _record(
        self,
        entity_type: AuditEntityType,
        entity_id: int | None,
        action_type: AuditActionType,
        context: AuditContext,
        details: dict[str, Any],
    ) -> AuditLog:
        audit_log = AuditLog(
            occurred_at=datetime.now(UTC),
            entity_type=entity_type,
            entity_id=entity_id,
            action_type=action_type,
            delivery_slip_id=context.delivery_slip_id,
            pallet_id=context.pallet_id,
            document_id=context.document_id,
            split_transport_id=context.split_transport_id,
            performed_by=context.performed_by,
            source_system=context.source_system,
            details_json=details,
        )
        return self._repository.add(audit_log)
