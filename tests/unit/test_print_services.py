"""Unit tests for print instruction and print job services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from logistics_app.application.services import (
    PrintInstructionService,
    PrintJobService,
    PrintRequest,
)
from logistics_app.data.models.document_print_instruction import DocumentPrintInstruction
from logistics_app.data.models.enums import (
    DocumentType,
    PrintJobStatus,
    PrintTargetType,
)
from logistics_app.data.models.print_job import PrintJob
from logistics_app.infrastructure.config.settings import (
    ApplicationSettings,
    PrinterDefaults,
    PrinterSettings,
)


@dataclass
class FakeSession:
    """Simple session double for service-level tests."""

    added_records: list[object] | None = None
    objects_by_key: dict[tuple[type[object], int], object] | None = None

    def __post_init__(self) -> None:
        if self.added_records is None:
            self.added_records = []
        if self.objects_by_key is None:
            self.objects_by_key = {}

    def add(self, record: object) -> None:
        self.added_records.append(record)
        if getattr(record, "id", None) is None:
            record.id = len(self.added_records)

    def get(self, model_class: type[object], identifier: int) -> object | None:
        return self.objects_by_key.get((model_class, identifier))

    def flush(self) -> None:
        return None

    def scalar(self, statement: object) -> object | None:
        return None

    def scalars(self, statement: object) -> list[object]:
        return []


class FakeDocumentPrintInstructionRepository:
    """Instruction repository double keyed by delivery and document type."""

    def __init__(self) -> None:
        self.instructions: dict[tuple[int, DocumentType, int | None], DocumentPrintInstruction] = {}

    def add(self, instruction: DocumentPrintInstruction) -> DocumentPrintInstruction:
        self.instructions[
            (instruction.delivery_slip_id, instruction.document_type, instruction.split_transport_id)
        ] = instruction
        return instruction

    def get_by_scope(
        self,
        delivery_slip_id: int,
        document_type: DocumentType,
        split_transport_id: int | None = None,
    ) -> DocumentPrintInstruction | None:
        return self.instructions.get((delivery_slip_id, document_type, split_transport_id))

    def list_by_delivery_slip(
        self,
        delivery_slip_id: int,
        split_transport_id: int | None = None,
    ) -> list[DocumentPrintInstruction]:
        return [
            instruction
            for (instruction_delivery_slip_id, _document_type, instruction_split_transport_id), instruction in self.instructions.items()
            if instruction_delivery_slip_id == delivery_slip_id
            and instruction_split_transport_id == split_transport_id
        ]


class FakePrintJobRepository:
    """Print job repository double for copy tracking tests."""

    def __init__(self) -> None:
        self.jobs: dict[int, PrintJob] = {}
        self.next_id = 1

    def add(self, print_job: PrintJob) -> PrintJob:
        if getattr(print_job, "id", None) is None:
            print_job.id = self.next_id
            self.next_id += 1
        self.jobs[print_job.id] = print_job
        return print_job

    def get_by_id(self, print_job_id: int) -> PrintJob | None:
        return self.jobs.get(print_job_id)

    def get_total_printed_copies(
        self,
        delivery_slip_id: int,
        document_type: DocumentType,
        split_transport_id: int | None = None,
    ) -> int:
        total = 0
        for print_job in self.jobs.values():
            if (
                print_job.delivery_slip_id == delivery_slip_id
                and print_job.document_type == document_type
                and print_job.split_transport_id == split_transport_id
                and print_job.status == PrintJobStatus.PRINTED
            ):
                total += print_job.printed_copy_count or 0
        return total

    def list_by_delivery_slip(
        self,
        delivery_slip_id: int,
        split_transport_id: int | None = None,
    ) -> list[PrintJob]:
        return [
            print_job
            for print_job in self.jobs.values()
            if print_job.delivery_slip_id == delivery_slip_id
            and print_job.split_transport_id == split_transport_id
        ]


def build_print_job_service() -> tuple[PrintInstructionService, PrintJobService, FakePrintJobRepository]:
    """Create print services wired with test doubles."""
    session = FakeSession()
    instruction_repository = FakeDocumentPrintInstructionRepository()
    print_job_repository = FakePrintJobRepository()

    instruction_service = PrintInstructionService(session)
    instruction_service._instruction_repository = instruction_repository
    instruction_service._print_job_repository = print_job_repository

    settings = ApplicationSettings.model_construct(
        printers=PrinterSettings(
            defaults=PrinterDefaults(
                warehouse_main_printer="Warehouse_Main_01",
                loading_dock_printer="Loading_Dock_01",
                office_printer="Office_01",
                label_printer="Label_01",
            )
        )
    )
    print_job_service = PrintJobService(session=session, settings=settings)
    print_job_service._instruction_service = instruction_service
    print_job_service._print_job_repository = print_job_repository
    return instruction_service, print_job_service, print_job_repository


def test_print_instruction_summary_tracks_remaining_copies() -> None:
    """Remaining copies should be required minus successfully printed copies."""
    instruction_service, _, print_job_repository = build_print_job_service()

    instruction_service.upsert_instruction(
        delivery_slip_id=10,
        document_type=DocumentType.CMR,
        required_copy_count=4,
        changed_by="transport.user",
        source_system="service_api",
    )
    print_job_repository.add(
        PrintJob(
            delivery_slip_id=10,
            document_type=DocumentType.CMR,
            target_type=PrintTargetType.DOCUMENT,
            printer_name="Warehouse_Main_01",
            requested_copy_count=2,
            printed_copy_count=2,
            status=PrintJobStatus.PRINTED,
            queued_at=datetime.now(UTC),
        )
    )

    summary = instruction_service.get_requirement_summary(
        delivery_slip_id=10,
        document_type=DocumentType.CMR,
    )

    assert summary.required_copy_count == 4
    assert summary.printed_copy_count == 2
    assert summary.remaining_copy_count == 2


def test_request_print_uses_remaining_copies_and_default_printer_mapping() -> None:
    """Warehouse print requests should use remaining copies and configured default routing."""
    instruction_service, print_job_service, _ = build_print_job_service()

    instruction_service.upsert_instruction(
        delivery_slip_id=20,
        document_type=DocumentType.PACKING_SLIP,
        required_copy_count=3,
        changed_by="transport.user",
        source_system="service_api",
    )

    print_job, summary = print_job_service.request_print(
        PrintRequest(
            delivery_slip_id=20,
            document_type=DocumentType.PACKING_SLIP,
            requested_by="warehouse.user",
            source_system="desktop_client",
        )
    )

    assert print_job.requested_copy_count == 3
    assert print_job.printer_name == "Warehouse_Main_01"
    assert print_job.is_manual_printer_override is False
    assert summary.remaining_copy_count == 3


def test_request_reprint_creates_new_job_with_override_printer() -> None:
    """Reprints should create a separate print job and allow manual printer override."""
    _, print_job_service, print_job_repository = build_print_job_service()

    original_job = PrintJob(
        id=5,
        delivery_slip_id=30,
        document_type=DocumentType.STICKER,
        target_type=PrintTargetType.DOCUMENT,
        printer_role="label_printer",
        printer_name="Label_01",
        requested_copy_count=2,
        printed_copy_count=2,
        status=PrintJobStatus.PRINTED,
        queued_at=datetime.now(UTC),
    )
    print_job_repository.add(original_job)

    reprint_job = print_job_service.request_reprint(
        print_job_id=5,
        requested_by="warehouse.user",
        source_system="desktop_client",
        printer_name_override="Label_Backup_01",
    )

    assert reprint_job.reprint_of_print_job_id == 5
    assert reprint_job.printer_name == "Label_Backup_01"
    assert reprint_job.is_manual_printer_override is True


def test_mark_job_printed_updates_printed_and_remaining_copy_counts() -> None:
    """A successfully printed job should reduce remaining required copies."""
    instruction_service, print_job_service, _ = build_print_job_service()

    instruction_service.upsert_instruction(
        delivery_slip_id=40,
        document_type=DocumentType.CMR,
        required_copy_count=2,
        changed_by="transport.user",
        source_system="service_api",
    )

    print_job, _summary = print_job_service.request_print(
        PrintRequest(
            delivery_slip_id=40,
            document_type=DocumentType.CMR,
            requested_by="warehouse.user",
            source_system="desktop_client",
        )
    )
    print_job_service.mark_job_printed(print_job.id, printed_copy_count=2)

    summary_after_print = instruction_service.get_requirement_summary(
        delivery_slip_id=40,
        document_type=DocumentType.CMR,
    )

    assert summary_after_print.printed_copy_count == 2
    assert summary_after_print.remaining_copy_count == 0


def test_print_summary_is_scoped_to_split_transport_when_exception_flow_is_used() -> None:
    """Rare split transport instructions should not affect the normal delivery scope."""
    instruction_service, _, print_job_repository = build_print_job_service()

    instruction_service.upsert_instruction(
        delivery_slip_id=50,
        document_type=DocumentType.PACKING_SLIP,
        required_copy_count=5,
        changed_by="transport.user",
        source_system="service_api",
        split_transport_id=7,
    )
    print_job_repository.add(
        PrintJob(
            delivery_slip_id=50,
            document_type=DocumentType.PACKING_SLIP,
            split_transport_id=7,
            target_type=PrintTargetType.SPLIT_TRANSPORT,
            printer_name="Warehouse_Main_01",
            requested_copy_count=2,
            printed_copy_count=2,
            status=PrintJobStatus.PRINTED,
            queued_at=datetime.now(UTC),
        )
    )
    print_job_repository.add(
        PrintJob(
            delivery_slip_id=50,
            document_type=DocumentType.PACKING_SLIP,
            split_transport_id=None,
            target_type=PrintTargetType.DELIVERY,
            printer_name="Warehouse_Main_01",
            requested_copy_count=3,
            printed_copy_count=3,
            status=PrintJobStatus.PRINTED,
            queued_at=datetime.now(UTC),
        )
    )

    split_summary = instruction_service.get_requirement_summary(
        delivery_slip_id=50,
        document_type=DocumentType.PACKING_SLIP,
        split_transport_id=7,
    )
    normal_summary = instruction_service.get_requirement_summary(
        delivery_slip_id=50,
        document_type=DocumentType.PACKING_SLIP,
    )

    assert split_summary.required_copy_count == 5
    assert split_summary.printed_copy_count == 2
    assert split_summary.remaining_copy_count == 3
    assert normal_summary.required_copy_count == 0
    assert normal_summary.printed_copy_count == 3
