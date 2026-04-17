"""Print job business logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from logistics_app.application.services.application_logging_service import (
    ApplicationLogContext,
    ApplicationLoggingService,
)
from logistics_app.application.services.audit_trail_service import AuditContext, AuditTrailService
from logistics_app.application.services.print_instruction_service import (
    PrintInstructionService,
    PrintRequirementSummary,
)
from logistics_app.data.models.enums import DocumentType, PrintJobStatus, PrintTargetType
from logistics_app.data.models.print_job import PrintJob
from logistics_app.data.repositories.print_job_repository import PrintJobRepository
from logistics_app.infrastructure.config.settings import ApplicationSettings, get_settings


@dataclass(frozen=True, slots=True)
class PrintRequest:
    """Request data for creating a print job."""

    delivery_slip_id: int
    document_type: DocumentType
    requested_by: str | None
    source_system: str | None
    document_id: int | None = None
    split_transport_id: int | None = None
    printer_name_override: str | None = None
    requested_copy_count: int | None = None


class PrintConfigurationError(Exception):
    """Raised when printer routing cannot be resolved cleanly."""


class PrintJobService:
    """Creates and updates warehouse print jobs."""

    def __init__(
        self,
        session: Session,
        settings: ApplicationSettings | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._instruction_service = PrintInstructionService(session)
        self._print_job_repository = PrintJobRepository(session)
        self._audit_trail_service = AuditTrailService(session)
        self._application_logging_service = ApplicationLoggingService(
            session=session,
            settings=self._settings,
        )

    def request_print(self, request: PrintRequest) -> tuple[PrintJob, PrintRequirementSummary]:
        """Create a print job for required remaining copies or a manual request."""
        requirement_summary = self._instruction_service.get_requirement_summary(
            delivery_slip_id=request.delivery_slip_id,
            document_type=request.document_type,
            split_transport_id=request.split_transport_id,
        )
        requested_copy_count = self._resolve_requested_copy_count(
            requested_copy_count=request.requested_copy_count,
            requirement_summary=requirement_summary,
        )
        printer_role = requirement_summary.printer_role or self._get_default_printer_role(
            request.document_type
        )
        printer_name = request.printer_name_override or self._get_printer_name_for_role(printer_role)

        print_job = PrintJob(
            delivery_slip_id=request.delivery_slip_id,
            document_id=request.document_id,
            document_type=request.document_type,
            split_transport_id=request.split_transport_id,
            target_type=self._resolve_target_type(request),
            printer_role=printer_role,
            printer_name=printer_name,
            is_manual_printer_override=request.printer_name_override is not None,
            requested_copy_count=requested_copy_count,
            printed_copy_count=0,
            status=PrintJobStatus.QUEUED,
            queued_at=datetime.now(UTC),
            requested_by=request.requested_by,
        )
        self._print_job_repository.add(print_job)
        self._session.flush()

        self._audit_trail_service.record_print_action_requested(
            print_job_id=print_job.id,
            printer_name=printer_name,
            requested_copy_count=requested_copy_count,
            context=AuditContext(
                performed_by=request.requested_by,
                source_system=request.source_system,
                delivery_slip_id=request.delivery_slip_id,
                document_id=request.document_id,
                split_transport_id=request.split_transport_id,
            ),
            document_type=request.document_type,
            printer_role=printer_role,
            is_manual_printer_override=request.printer_name_override is not None,
        )
        return print_job, self._instruction_service.get_requirement_summary(
            delivery_slip_id=request.delivery_slip_id,
            document_type=request.document_type,
            split_transport_id=request.split_transport_id,
        )

    def request_reprint(
        self,
        print_job_id: int,
        requested_by: str | None,
        source_system: str | None,
        requested_copy_count: int | None = None,
        printer_name_override: str | None = None,
    ) -> PrintJob:
        """Create a reprint job from an existing print job."""
        original_print_job = self._print_job_repository.get_by_id(print_job_id)
        if original_print_job is None:
            raise PrintConfigurationError(f"Print job {print_job_id} was not found.")

        reprint_copy_count = requested_copy_count or original_print_job.printed_copy_count or original_print_job.requested_copy_count
        printer_name = printer_name_override or original_print_job.printer_name

        reprint_job = PrintJob(
            delivery_slip_id=original_print_job.delivery_slip_id,
            document_id=original_print_job.document_id,
            document_type=original_print_job.document_type,
            split_transport_id=original_print_job.split_transport_id,
            target_type=original_print_job.target_type,
            printer_role=original_print_job.printer_role,
            printer_name=printer_name,
            is_manual_printer_override=printer_name_override is not None,
            requested_copy_count=reprint_copy_count,
            printed_copy_count=0,
            reprint_of_print_job_id=original_print_job.id,
            status=PrintJobStatus.QUEUED,
            queued_at=datetime.now(UTC),
            requested_by=requested_by,
        )
        self._print_job_repository.add(reprint_job)
        self._session.flush()

        self._audit_trail_service.record_print_action_requested(
            print_job_id=reprint_job.id,
            printer_name=printer_name,
            requested_copy_count=reprint_copy_count,
            context=AuditContext(
                performed_by=requested_by,
                source_system=source_system,
                delivery_slip_id=original_print_job.delivery_slip_id,
                document_id=original_print_job.document_id,
                split_transport_id=original_print_job.split_transport_id,
            ),
            document_type=original_print_job.document_type,
            printer_role=original_print_job.printer_role,
            is_reprint=True,
            is_manual_printer_override=printer_name_override is not None,
        )
        return reprint_job

    def mark_job_sent(self, print_job_id: int) -> PrintJob:
        """Mark a print job as sent to the printer subsystem."""
        print_job = self._require_print_job(print_job_id)
        print_job.status = PrintJobStatus.SENT
        print_job.started_at = datetime.now(UTC)
        return print_job

    def mark_job_printed(self, print_job_id: int, printed_copy_count: int) -> PrintJob:
        """Mark a print job as completed successfully."""
        print_job = self._require_print_job(print_job_id)
        print_job.status = PrintJobStatus.PRINTED
        print_job.printed_copy_count = printed_copy_count
        print_job.completed_at = datetime.now(UTC)
        return print_job

    def mark_job_failed(
        self,
        print_job_id: int,
        error_message: str,
        source_system: str | None = None,
    ) -> PrintJob:
        """Mark a print job as failed and emit an application log."""
        print_job = self._require_print_job(print_job_id)
        print_job.status = PrintJobStatus.FAILED
        print_job.error_message = error_message
        print_job.completed_at = datetime.now(UTC)
        self._application_logging_service.log_print_failure(
            message=error_message,
            context=ApplicationLogContext(
                acting_user=print_job.requested_by,
                delivery_slip_id=print_job.delivery_slip_id,
                document_id=print_job.document_id,
                source_system=source_system,
                extra_data={
                    "event_name": "print_job_failed",
                    "print_job_id": print_job.id,
                    "document_type": print_job.document_type.value,
                    "printer_name": print_job.printer_name,
                },
            ),
        )
        return print_job

    def list_jobs(
        self,
        delivery_slip_id: int,
        split_transport_id: int | None = None,
    ) -> list[PrintJob]:
        """Return print jobs for one delivery scope."""
        return self._print_job_repository.list_by_delivery_slip(
            delivery_slip_id=delivery_slip_id,
            split_transport_id=split_transport_id,
        )

    def _resolve_requested_copy_count(
        self,
        requested_copy_count: int | None,
        requirement_summary: PrintRequirementSummary,
    ) -> int:
        if requested_copy_count is not None:
            return requested_copy_count
        if requirement_summary.remaining_copy_count > 0:
            return requirement_summary.remaining_copy_count
        raise PrintConfigurationError(
            "No remaining required copies are available. Use a reprint request or provide an explicit copy count."
        )

    def _resolve_target_type(self, request: PrintRequest) -> PrintTargetType:
        if request.document_id is not None:
            return PrintTargetType.DOCUMENT
        if request.split_transport_id is not None:
            return PrintTargetType.SPLIT_TRANSPORT
        return PrintTargetType.DELIVERY

    def _get_default_printer_role(self, document_type: DocumentType) -> str:
        mapping = self._settings.printers.document_type_mapping
        role_attribute_name = {
            DocumentType.PACKING_SLIP: mapping.packing_slip,
            DocumentType.CMR: mapping.cmr,
            DocumentType.SIGNED_CMR: mapping.signed_cmr,
            DocumentType.CERTIFICATE: mapping.certificate,
            DocumentType.STICKER: mapping.sticker,
            DocumentType.TRANSPORT_DOCUMENT: mapping.transport_document,
            DocumentType.OTHER: mapping.other,
        }[document_type]
        return role_attribute_name

    def _get_printer_name_for_role(self, printer_role: str) -> str:
        defaults = self._settings.printers.defaults
        if not hasattr(defaults, printer_role):
            raise PrintConfigurationError(
                f"Printer role '{printer_role}' is not configured in printer defaults."
            )
        printer_name = getattr(defaults, printer_role)
        if not printer_name:
            raise PrintConfigurationError(
                f"Printer role '{printer_role}' does not resolve to a printer name."
            )
        return printer_name

    def _require_print_job(self, print_job_id: int) -> PrintJob:
        print_job = self._print_job_repository.get_by_id(print_job_id)
        if print_job is None:
            raise PrintConfigurationError(f"Print job {print_job_id} was not found.")
        return print_job
