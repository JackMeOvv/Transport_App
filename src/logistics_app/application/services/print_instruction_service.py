"""Print instruction business logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from logistics_app.application.services.audit_trail_service import AuditContext, AuditTrailService
from logistics_app.data.models.document_print_instruction import DocumentPrintInstruction
from logistics_app.data.models.enums import DocumentType
from logistics_app.data.repositories.document_print_instruction_repository import (
    DocumentPrintInstructionRepository,
)
from logistics_app.data.repositories.print_job_repository import PrintJobRepository


@dataclass(frozen=True, slots=True)
class PrintRequirementSummary:
    """Operational summary of required, printed, and remaining copies."""

    delivery_slip_id: int
    document_type: DocumentType
    split_transport_id: int | None
    required_copy_count: int
    printed_copy_count: int
    remaining_copy_count: int
    printer_role: str | None
    is_mandatory: bool


class PrintInstructionService:
    """Manages transport-defined print copy requirements."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._instruction_repository = DocumentPrintInstructionRepository(session)
        self._print_job_repository = PrintJobRepository(session)
        self._audit_trail_service = AuditTrailService(session)

    def upsert_instruction(
        self,
        delivery_slip_id: int,
        document_type: DocumentType,
        required_copy_count: int,
        changed_by: str | None,
        source_system: str | None,
        split_transport_id: int | None = None,
        printer_role: str | None = None,
        is_mandatory: bool = True,
        notes: str | None = None,
    ) -> DocumentPrintInstruction:
        """Create or update a transport-defined print instruction."""
        instruction = self._instruction_repository.get_by_scope(
            delivery_slip_id=delivery_slip_id,
            document_type=document_type,
            split_transport_id=split_transport_id,
        )
        if instruction is None:
            instruction = DocumentPrintInstruction(
                delivery_slip_id=delivery_slip_id,
                split_transport_id=split_transport_id,
                document_type=document_type,
                required_copy_count=required_copy_count,
                printer_role=printer_role,
                is_mandatory=is_mandatory,
                notes=notes,
                created_by=changed_by,
                updated_by=changed_by,
            )
            self._instruction_repository.add(instruction)
        else:
            instruction.required_copy_count = required_copy_count
            instruction.printer_role = printer_role
            instruction.is_mandatory = is_mandatory
            instruction.notes = notes
            instruction.updated_at = datetime.now(UTC)
            instruction.updated_by = changed_by

        self._audit_trail_service.record_print_instruction_changed(
            delivery_slip_id=delivery_slip_id,
            document_type=document_type,
            required_copy_count=required_copy_count,
            printer_role=printer_role,
            context=AuditContext(
                performed_by=changed_by,
                source_system=source_system,
                delivery_slip_id=delivery_slip_id,
                split_transport_id=split_transport_id,
            ),
        )
        return instruction

    def get_requirement_summary(
        self,
        delivery_slip_id: int,
        document_type: DocumentType,
        split_transport_id: int | None = None,
    ) -> PrintRequirementSummary:
        """Return required, printed, and remaining copies for a document type."""
        instruction = self._instruction_repository.get_by_scope(
            delivery_slip_id=delivery_slip_id,
            document_type=document_type,
            split_transport_id=split_transport_id,
        )
        required_copy_count = instruction.required_copy_count if instruction is not None else 0
        printed_copy_count = self._print_job_repository.get_total_printed_copies(
            delivery_slip_id=delivery_slip_id,
            document_type=document_type,
            split_transport_id=split_transport_id,
        )
        remaining_copy_count = max(required_copy_count - printed_copy_count, 0)
        return PrintRequirementSummary(
            delivery_slip_id=delivery_slip_id,
            document_type=document_type,
            split_transport_id=split_transport_id,
            required_copy_count=required_copy_count,
            printed_copy_count=printed_copy_count,
            remaining_copy_count=remaining_copy_count,
            printer_role=instruction.printer_role if instruction is not None else None,
            is_mandatory=instruction.is_mandatory if instruction is not None else False,
        )
