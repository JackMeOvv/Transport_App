"""Desktop-facing printing service layer."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from logistics_app.application.services.print_job_service import PrintJobService
from logistics_app.infrastructure.config.settings import ApplicationSettings, get_settings
from logistics_app.infrastructure.printing.printing_exceptions import (
    PrintableFileNotFoundError,
    PrintExecutionError,
)
from logistics_app.infrastructure.printing.printing_models import (
    DesktopPrintExecutionRequest,
    DesktopReprintExecutionRequest,
    PrintExecutionResult,
    PrinterInfo,
)
from logistics_app.infrastructure.printing.windows_print_backend import WindowsPrintBackend
from logistics_app.infrastructure.printing.workstation_print_backend import WorkstationPrintBackend


class DesktopPrintService:
    """Coordinates workstation print execution with print job tracking.

    Business logic decides what should be printed. This service performs the
    local workstation print call and reports the outcome back into `print_jobs`.
    """

    def __init__(
        self,
        session: Session,
        settings: ApplicationSettings | None = None,
        backend: WorkstationPrintBackend | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._backend = backend or self._build_backend()
        self._print_job_service = PrintJobService(session=session, settings=self._settings)

    def list_available_printers(self) -> list[PrinterInfo]:
        """Return printers available on the current workstation."""
        return self._backend.list_printers()

    def request_and_execute_print(
        self,
        request: DesktopPrintExecutionRequest,
    ) -> PrintExecutionResult:
        """Create a print job and execute it on the workstation."""
        print_job, _ = self._print_job_service.request_print(request.print_request)
        return self._execute_print_job(
            print_job_id=print_job.id,
            document_file_path=request.document_file_path,
        )

    def request_and_execute_reprint(
        self,
        request: DesktopReprintExecutionRequest,
    ) -> PrintExecutionResult:
        """Create a reprint job and execute it on the workstation."""
        reprint_job = self._print_job_service.request_reprint(
            print_job_id=request.original_print_job_id,
            requested_by=request.requested_by,
            source_system=request.source_system,
            requested_copy_count=request.requested_copy_count,
            printer_name_override=request.printer_name_override,
        )
        return self._execute_print_job(
            print_job_id=reprint_job.id,
            document_file_path=request.document_file_path,
        )

    def execute_existing_print_job(
        self,
        print_job_id: int,
        document_file_path: Path,
    ) -> PrintExecutionResult:
        """Execute an already queued print job from the local workstation."""
        return self._execute_print_job(
            print_job_id=print_job_id,
            document_file_path=document_file_path,
        )

    def _execute_print_job(
        self,
        print_job_id: int,
        document_file_path: Path,
    ) -> PrintExecutionResult:
        print_job = self._print_job_service.mark_job_sent(print_job_id)
        try:
            self._ensure_document_file_exists(document_file_path)
            self._backend.print_file(
                file_path=document_file_path,
                printer_name=print_job.printer_name,
                copy_count=print_job.requested_copy_count,
            )
            self._print_job_service.mark_job_printed(
                print_job_id=print_job_id,
                printed_copy_count=print_job.requested_copy_count,
            )
            return PrintExecutionResult(
                print_job_id=print_job_id,
                printer_name=print_job.printer_name,
                requested_copy_count=print_job.requested_copy_count,
                printed_copy_count=print_job.requested_copy_count,
                succeeded=True,
            )
        except Exception as exc:
            error_message = self._format_error_message(exc)
            self._print_job_service.mark_job_failed(
                print_job_id=print_job_id,
                error_message=error_message,
                source_system="desktop_client",
            )
            return PrintExecutionResult(
                print_job_id=print_job_id,
                printer_name=print_job.printer_name,
                requested_copy_count=print_job.requested_copy_count,
                printed_copy_count=0,
                succeeded=False,
                error_message=error_message,
            )

    def _build_backend(self) -> WorkstationPrintBackend:
        if self._settings.printers.spooler_backend.lower() != "windows":
            raise PrintExecutionError(
                "Only the Windows workstation print backend is currently supported."
            )
        return WindowsPrintBackend()

    def _ensure_document_file_exists(self, document_file_path: Path) -> None:
        if not document_file_path.exists() or not document_file_path.is_file():
            raise PrintableFileNotFoundError(
                f"Print file does not exist on the workstation: {document_file_path}"
            )

    def _format_error_message(self, exception: Exception) -> str:
        if isinstance(exception, PrintExecutionError):
            return str(exception)
        return f"Unexpected print failure: {exception}"
