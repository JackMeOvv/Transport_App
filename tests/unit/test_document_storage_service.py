"""Unit tests for document storage behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from logistics_app.data.models.delivery_slip import DeliverySlip
from logistics_app.data.models.document import Document
from logistics_app.data.models.enums import DocumentStatus, DocumentType, DeliverySlipStatus, PalletStatus
from logistics_app.data.models.pallet import Pallet
from logistics_app.infrastructure.config.settings import (
    ApiSettings,
    ApplicationSettings,
    DatabaseSettings,
    DesktopSettings,
    LoggingSettings,
    PrinterSettings,
    StorageSettings,
)
from logistics_app.infrastructure.storage.document_storage_service import (
    DocumentLinkValidationError,
    DocumentStorageService,
    StoreDocumentRequest,
)


@dataclass
class FakeDocumentRepository:
    """Minimal repository double for unit testing the storage service."""

    latest_documents: dict[tuple[int, DocumentType, int | None, int | None], Document] | None = None
    added_documents: list[Document] | None = None
    mark_not_latest_calls: list[tuple[int, DocumentType, int | None, int | None]] | None = None

    def __post_init__(self) -> None:
        if self.latest_documents is None:
            self.latest_documents = {}
        if self.added_documents is None:
            self.added_documents = []
        if self.mark_not_latest_calls is None:
            self.mark_not_latest_calls = []

    def add(self, document: Document) -> Document:
        self.added_documents.append(document)
        self.latest_documents[
            (
                document.delivery_slip_id,
                document.document_type,
                document.pallet_id,
                document.split_transport_id,
            )
        ] = document
        return document

    def get_latest_version(
        self,
        delivery_slip_id: int,
        document_type: DocumentType,
        pallet_id: int | None = None,
        split_transport_id: int | None = None,
    ) -> Document | None:
        return self.latest_documents.get(
            (delivery_slip_id, document_type, pallet_id, split_transport_id)
        )

    def mark_existing_versions_not_latest(
        self,
        delivery_slip_id: int,
        document_type: DocumentType,
        pallet_id: int | None = None,
        split_transport_id: int | None = None,
    ) -> None:
        self.mark_not_latest_calls.append(
            (delivery_slip_id, document_type, pallet_id, split_transport_id)
        )
        latest_document = self.latest_documents.get(
            (delivery_slip_id, document_type, pallet_id, split_transport_id)
        )
        if latest_document is not None:
            latest_document.is_latest_version = False


class FakeSession:
    """Minimal session double for service-level unit tests."""

    def __init__(self, objects_by_key: dict[tuple[type[object], int], object]) -> None:
        self._objects_by_key = objects_by_key

    def get(self, model_class: type[object], identifier: int) -> object | None:
        return self._objects_by_key.get((model_class, identifier))

    def flush(self) -> None:
        return None


def build_settings(documents_root: Path) -> ApplicationSettings:
    """Create deterministic settings for storage tests."""
    return ApplicationSettings.model_construct(
        environment="test",
        database=DatabaseSettings(),
        storage=StorageSettings(
            documents_root=documents_root,
            temporary_files_root=documents_root / "temp",
            exports_root=documents_root / "exports",
        ),
        printers=PrinterSettings(),
        api=ApiSettings(),
        desktop=DesktopSettings(),
        logging=LoggingSettings(),
    )


def test_store_document_preserves_original_name_and_creates_versioned_metadata() -> None:
    """A normal upload stores a file externally and creates metadata only in the ORM entity."""
    with TemporaryDirectory() as temporary_directory:
        root_path = Path(temporary_directory)
        source_file_path = root_path / "Packing Slip 001.pdf"
        source_content = b"packing-slip-content"
        source_file_path.write_bytes(source_content)

        delivery_slip = DeliverySlip(
            id=10,
            delivery_slip_number="DEL-2026-0001",
            status=DeliverySlipStatus.CREATED,
        )
        session = FakeSession({(DeliverySlip, 10): delivery_slip})
        repository = FakeDocumentRepository()
        service = DocumentStorageService(session=session, settings=build_settings(root_path / "docs"))
        service._repository = repository

        document = service.store_document(
            StoreDocumentRequest(
                delivery_slip_id=10,
                document_type=DocumentType.PACKING_SLIP,
                source_file_path=source_file_path,
                uploaded_by="warehouse.user",
                document_date=date(2026, 4, 16),
            )
        )

        stored_file_path = service._settings.storage.documents_root / document.storage_relative_path
        assert document.original_filename == "Packing Slip 001.pdf"
        assert document.document_status == DocumentStatus.AVAILABLE
        assert document.version_number == 1
        assert document.is_latest_version is True
        assert stored_file_path.exists()
        assert stored_file_path.read_bytes() == source_content
        assert document.stored_filename != document.original_filename
        assert "packing_slip_v001" in document.stored_filename
        assert document.checksum_sha256 == hashlib.sha256(source_content).hexdigest()


def test_storing_new_version_marks_previous_version_not_latest() -> None:
    """Uploading a second file for the same scope creates a new version instead of overwriting."""
    with TemporaryDirectory() as temporary_directory:
        root_path = Path(temporary_directory)
        first_source_file_path = root_path / "cmr-original.pdf"
        second_source_file_path = root_path / "cmr-updated.pdf"
        first_source_file_path.write_bytes(b"first")
        second_source_file_path.write_bytes(b"second")

        delivery_slip = DeliverySlip(
            id=20,
            delivery_slip_number="DEL-2026-0002",
            status=DeliverySlipStatus.CREATED,
        )
        existing_document = Document(
            delivery_slip_id=20,
            document_type=DocumentType.CMR,
            document_status=DocumentStatus.AVAILABLE,
            original_filename="cmr-original.pdf",
            stored_filename="cmr_v001_original.pdf",
            storage_relative_path="DEL-2026-0002/cmr/cmr_v001_original.pdf",
            version_number=1,
            is_latest_version=True,
        )

        session = FakeSession({(DeliverySlip, 20): delivery_slip})
        repository = FakeDocumentRepository(
            latest_documents={(20, DocumentType.CMR, None, None): existing_document}
        )
        service = DocumentStorageService(session=session, settings=build_settings(root_path / "docs"))
        service._repository = repository

        new_document = service.store_document(
            StoreDocumentRequest(
                delivery_slip_id=20,
                document_type=DocumentType.CMR,
                source_file_path=second_source_file_path,
            )
        )

        assert existing_document.is_latest_version is False
        assert new_document.version_number == 2
        assert new_document.stored_filename != existing_document.stored_filename


def test_signed_cmr_is_stored_separately_from_original_cmr() -> None:
    """A signed CMR uses a separate document type and does not replace the original CMR."""
    with TemporaryDirectory() as temporary_directory:
        root_path = Path(temporary_directory)
        original_cmr_file_path = root_path / "cmr.pdf"
        signed_cmr_file_path = root_path / "signed-cmr.pdf"
        original_cmr_file_path.write_bytes(b"original cmr")
        signed_cmr_file_path.write_bytes(b"signed cmr")

        delivery_slip = DeliverySlip(
            id=30,
            delivery_slip_number="DEL-2026-0003",
            status=DeliverySlipStatus.CREATED,
        )

        session = FakeSession({(DeliverySlip, 30): delivery_slip})
        repository = FakeDocumentRepository()
        service = DocumentStorageService(session=session, settings=build_settings(root_path / "docs"))
        service._repository = repository

        original_document = service.store_document(
            StoreDocumentRequest(
                delivery_slip_id=30,
                document_type=DocumentType.CMR,
                source_file_path=original_cmr_file_path,
            )
        )
        signed_document = service.store_document(
            StoreDocumentRequest(
                delivery_slip_id=30,
                document_type=DocumentType.SIGNED_CMR,
                source_file_path=signed_cmr_file_path,
            )
        )

        assert original_document.document_type == DocumentType.CMR
        assert signed_document.document_type == DocumentType.SIGNED_CMR
        assert original_document.stored_filename != signed_document.stored_filename
        assert original_document.storage_relative_path != signed_document.storage_relative_path
        assert original_document.version_number == 1
        assert signed_document.version_number == 1


def test_store_document_rejects_pallet_from_another_delivery() -> None:
    """A pallet link must match the delivery that owns the document."""
    with TemporaryDirectory() as temporary_directory:
        root_path = Path(temporary_directory)
        source_file_path = root_path / "certificate.pdf"
        source_file_path.write_bytes(b"certificate")

        delivery_slip = DeliverySlip(
            id=40,
            delivery_slip_number="DEL-2026-0004",
            status=DeliverySlipStatus.CREATED,
        )
        pallet = Pallet(
            id=900,
            delivery_slip_id=999,
            pallet_identifier="PALLET-900",
            status=PalletStatus.REGISTERED,
        )

        session = FakeSession(
            {
                (DeliverySlip, 40): delivery_slip,
                (Pallet, 900): pallet,
            }
        )
        service = DocumentStorageService(session=session, settings=build_settings(root_path / "docs"))
        service._repository = FakeDocumentRepository()

        try:
            service.store_document(
                StoreDocumentRequest(
                    delivery_slip_id=40,
                    pallet_id=900,
                    document_type=DocumentType.CERTIFICATE,
                    source_file_path=source_file_path,
                )
            )
        except DocumentLinkValidationError:
            return

        raise AssertionError("Expected DocumentLinkValidationError for pallet mismatch.")
