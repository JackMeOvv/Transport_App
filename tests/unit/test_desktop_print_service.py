"""Unit tests for the desktop print service layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from logistics_app.data.models.enums import DocumentType, PrintJobStatus, PrintTargetType
from logistics_app.data.models.print_job import PrintJob
from logistics_app.infrastructure.printing.desktop_print_service import DesktopPrintService
from logistics_app.infrastructure.printing.printing_exceptions import (
    PrintExecutionError,
    PrintableFileNotFoundError,
)
from logistics_app.infrastructure.printing.printing_models import (
    DesktopPrintExecutionRequest,
    DesktopReprintExecutionRequest,
    PrinterInfo,
)


@dataclass
class FakeBackend:
    """Backend double for workstation printing tests."""

    should_fail: bool = False
    last_printer_name: str | None = None
    last_copy_count: int | None = None
    printers: list[PrinterInfo] | None = None

    def __post_init__(self) -> None:
        if self.printers is None:
            self.printers = [PrinterInfo(printer_name="Warehouse_Main_01", is_default=True)]

    def list_printers(self) -> list[PrinterInfo]:
        return self.printers

    def print_file(self, file_path: Path, printer_name: str, copy_count: int) -> None:
        self.last_printer_name = printer_name
        self.last_copy_count = copy_count
        if self.should_fail:
            raise PrintExecutionError("Printer spooler is unavailable.")


@dataclass
class FakePrintJobService:
    """Print job service double used to verify service orchestration."""

    request_print_result: PrintJob | None = None
    request_reprint_result: PrintJob | None = None
    sent_job_ids: list[int] | None = None
    printed_updates: list[tuple[int, int]] | None = None
    failed_updates: list[tuple[int, str, str | None]] | None = None

    def __post_init__(self) -> None:
        if self.sent_job_ids is None:
            self.sent_job_ids = []
        if self.printed_updates is None:
            self.printed_updates = []
        if self.failed_updates is None:
            self.failed_updates = []

    def request_print(self, request: object) -> tuple[PrintJob, object]:
        return self.request_print_result, object()

    def request_reprint(
        self,
        print_job_id: int,
        requested_by: str | None,
        source_system: str | None,
        requested_copy_count: int | None = None,
        printer_name_override: str | None = None,
    ) -> PrintJob:
        return self.request_reprint_result

    def mark_job_sent(self, print_job_id: int) -> PrintJob:
        self.sent_job_ids.append(print_job_id)
        if self.request_print_result is not None and self.request_print_result.id == print_job_id:
            return self.request_print_result
        return self.request_reprint_result

    def mark_job_printed(self, print_job_id: int, printed_copy_count: int) -> PrintJob:
        self.printed_updates.append((print_job_id, printed_copy_count))
        return self.mark_job_sent(print_job_id)

    def mark_job_failed(
        self,
        print_job_id: int,
        error_message: str,
        source_system: str | None = None,
    ) -> PrintJob:
        self.failed_updates.append((print_job_id, error_message, source_system))
        return self.mark_job_sent(print_job_id)


def test_execute_existing_print_job_marks_success() -> None:
    """Successful workstation printing should update the print job as printed."""
    with TemporaryDirectory() as temporary_directory:
        document_file_path = Path(temporary_directory) / "packing-slip.pdf"
        document_file_path.write_text("print me", encoding="utf-8")

        backend = FakeBackend()
        print_job = PrintJob(
            id=10,
            delivery_slip_id=1,
            document_type=DocumentType.PACKING_SLIP,
            target_type=PrintTargetType.DOCUMENT,
            printer_role="warehouse_main_printer",
            printer_name="Warehouse_Main_01",
            requested_copy_count=3,
            printed_copy_count=0,
            status=PrintJobStatus.QUEUED,
            queued_at=None,  # type: ignore[arg-type]
        )
        fake_print_job_service = FakePrintJobService(request_print_result=print_job)
        desktop_print_service = DesktopPrintService(session=None, backend=backend)  # type: ignore[arg-type]
        desktop_print_service._print_job_service = fake_print_job_service

        result = desktop_print_service.execute_existing_print_job(
            print_job_id=10,
            document_file_path=document_file_path,
        )

        assert result.succeeded is True
        assert result.printed_copy_count == 3
        assert backend.last_printer_name == "Warehouse_Main_01"
        assert backend.last_copy_count == 3
        assert fake_print_job_service.printed_updates == [(10, 3)]


def test_request_and_execute_reprint_marks_failure_on_backend_error() -> None:
    """Backend failures should be reflected back into print job failure tracking."""
    with TemporaryDirectory() as temporary_directory:
        document_file_path = Path(temporary_directory) / "sticker.pdf"
        document_file_path.write_text("reprint me", encoding="utf-8")

        backend = FakeBackend(should_fail=True)
        reprint_job = PrintJob(
            id=25,
            delivery_slip_id=2,
            document_type=DocumentType.STICKER,
            target_type=PrintTargetType.DOCUMENT,
            printer_role="label_printer",
            printer_name="Label_01",
            requested_copy_count=2,
            printed_copy_count=0,
            status=PrintJobStatus.QUEUED,
            queued_at=None,  # type: ignore[arg-type]
        )
        fake_print_job_service = FakePrintJobService(request_reprint_result=reprint_job)
        desktop_print_service = DesktopPrintService(session=None, backend=backend)  # type: ignore[arg-type]
        desktop_print_service._print_job_service = fake_print_job_service

        result = desktop_print_service.request_and_execute_reprint(
            DesktopReprintExecutionRequest(
                original_print_job_id=11,
                document_file_path=document_file_path,
                requested_by="warehouse.user",
                source_system="desktop_client",
            )
        )

        assert result.succeeded is False
        assert "Printer spooler is unavailable." in result.error_message
        assert fake_print_job_service.failed_updates[0][0] == 25


def test_execute_existing_print_job_rejects_missing_file() -> None:
    """Missing local files should fail cleanly before the workstation backend is called."""
    backend = FakeBackend()
    print_job = PrintJob(
        id=30,
        delivery_slip_id=3,
        document_type=DocumentType.CMR,
        target_type=PrintTargetType.DOCUMENT,
        printer_role="warehouse_main_printer",
        printer_name="Warehouse_Main_01",
        requested_copy_count=1,
        printed_copy_count=0,
        status=PrintJobStatus.QUEUED,
        queued_at=None,  # type: ignore[arg-type]
    )
    fake_print_job_service = FakePrintJobService(request_print_result=print_job)
    desktop_print_service = DesktopPrintService(session=None, backend=backend)  # type: ignore[arg-type]
    desktop_print_service._print_job_service = fake_print_job_service

    result = desktop_print_service.execute_existing_print_job(
        print_job_id=30,
        document_file_path=Path("C:/does-not-exist/document.pdf"),
    )

    assert result.succeeded is False
    assert "does not exist on the workstation" in result.error_message
