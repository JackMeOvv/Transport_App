"""Unit tests for document upload coordination."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from logistics_app.application.services.document_upload_service import (
    DocumentUploadRequest,
    DocumentUploadService,
)
from logistics_app.data.models.document import Document
from logistics_app.data.models.enums import DocumentStatus, DocumentType
from logistics_app.infrastructure.config.settings import (
    ApiSettings,
    ApplicationSettings,
    DatabaseSettings,
    DesktopSettings,
    LoggingSettings,
    PrinterSettings,
    StorageSettings,
)
from logistics_app.infrastructure.storage.document_storage_service import StoreDocumentRequest


@dataclass
class FakeStorageService:
    """Test double that captures document storage requests."""

    returned_document: Document
    received_requests: list[StoreDocumentRequest] = field(default_factory=list)
    received_file_bytes: list[bytes] = field(default_factory=list)
    error_to_raise: Exception | None = None

    def store_document(self, request: StoreDocumentRequest) -> Document:
        self.received_requests.append(request)
        self.received_file_bytes.append(request.source_file_path.read_bytes())
        if self.error_to_raise is not None:
            raise self.error_to_raise
        return self.returned_document


@dataclass
class FakeAuditTrailService:
    """Minimal audit trail double for upload coordination tests."""

    upload_calls: list[dict[str, object]] = field(default_factory=list)

    def record_document_uploaded(
        self,
        document_id: int,
        document_type: DocumentType,
        version_number: int,
        context: object,
    ) -> None:
        self.upload_calls.append(
            {
                "document_id": document_id,
                "document_type": document_type,
                "version_number": version_number,
                "context": context,
            }
        )


@dataclass
class FakeApplicationLoggingService:
    """Minimal application logging double for upload failure tests."""

    storage_failures: list[dict[str, object]] = field(default_factory=list)

    def log_storage_failure(
        self,
        message: str,
        exception: Exception,
        context: object,
    ) -> None:
        self.storage_failures.append(
            {
                "message": message,
                "exception": exception,
                "context": context,
            }
        )


class FakeSession:
    """Placeholder session object for service construction."""


def build_settings(root_path: Path) -> ApplicationSettings:
    """Create deterministic settings for document upload tests."""
    return ApplicationSettings.model_construct(
        environment="test",
        database=DatabaseSettings(),
        storage=StorageSettings(
            documents_root=root_path / "documents",
            temporary_files_root=root_path / "temp",
            exports_root=root_path / "exports",
        ),
        printers=PrinterSettings(),
        api=ApiSettings(),
        desktop=DesktopSettings(),
        logging=LoggingSettings(persist_application_logs=False),
    )


def build_document(document_type: DocumentType) -> Document:
    """Create a deterministic stored document for assertions."""
    return Document(
        id=500,
        delivery_slip_id=100,
        pallet_id=None,
        split_transport_id=None,
        document_type=document_type,
        document_status=DocumentStatus.AVAILABLE,
        original_filename="source.pdf",
        stored_filename="stored.pdf",
        storage_relative_path="DEL-2026-0001/cmr/stored.pdf",
        version_number=2,
        is_latest_version=True,
        uploaded_by="warehouse.user",
    )


def test_upload_document_passes_metadata_to_storage_and_cleans_temp_file() -> None:
    """Upload coordination should preserve metadata and clean temporary files afterwards."""
    with TemporaryDirectory() as temporary_directory:
        root_path = Path(temporary_directory)
        settings = build_settings(root_path)
        service = DocumentUploadService(session=FakeSession(), settings=settings)
        fake_storage_service = FakeStorageService(returned_document=build_document(DocumentType.CERTIFICATE))
        fake_audit_service = FakeAuditTrailService()
        fake_logging_service = FakeApplicationLoggingService()
        service._storage_service = fake_storage_service
        service._audit_trail_service = fake_audit_service
        service._application_logging_service = fake_logging_service

        document = service.upload_document(
            DocumentUploadRequest(
                delivery_slip_id=100,
                document_type=DocumentType.CERTIFICATE,
                original_filename="certificate-original.pdf",
                file_bytes=b"certificate-content",
                uploaded_by="warehouse.user",
                source_system="desktop_client",
                remarks="Loaded at dock 2",
                document_date=date(2026, 4, 17),
            )
        )

        storage_request = fake_storage_service.received_requests[0]
        assert storage_request.delivery_slip_id == 100
        assert storage_request.document_type == DocumentType.CERTIFICATE
        assert storage_request.uploaded_by == "warehouse.user"
        assert storage_request.remarks == "Loaded at dock 2"
        assert storage_request.document_date == date(2026, 4, 17)
        assert fake_storage_service.received_file_bytes == [b"certificate-content"]
        assert fake_audit_service.upload_calls[0]["document_type"] == DocumentType.CERTIFICATE
        assert document.document_type == DocumentType.CERTIFICATE
        assert list(settings.storage.temporary_files_root.glob("*")) == []
        assert fake_logging_service.storage_failures == []


def test_upload_signed_cmr_keeps_signed_document_type_in_audit_and_storage_flow() -> None:
    """Signed CMR uploads should remain a distinct document type through coordination."""
    with TemporaryDirectory() as temporary_directory:
        root_path = Path(temporary_directory)
        settings = build_settings(root_path)
        service = DocumentUploadService(session=FakeSession(), settings=settings)
        fake_storage_service = FakeStorageService(returned_document=build_document(DocumentType.SIGNED_CMR))
        fake_audit_service = FakeAuditTrailService()
        service._storage_service = fake_storage_service
        service._audit_trail_service = fake_audit_service
        service._application_logging_service = FakeApplicationLoggingService()

        service.upload_document(
            DocumentUploadRequest(
                delivery_slip_id=100,
                document_type=DocumentType.SIGNED_CMR,
                original_filename="signed-cmr.pdf",
                file_bytes=b"signed-cmr-content",
                uploaded_by="warehouse.user",
                source_system="desktop_client",
            )
        )

        assert fake_storage_service.received_requests[0].document_type == DocumentType.SIGNED_CMR
        assert fake_audit_service.upload_calls[0]["document_type"] == DocumentType.SIGNED_CMR


def test_upload_document_logs_failure_and_cleans_temp_file_when_storage_fails() -> None:
    """Storage failures should be logged and should not leave temporary files behind."""
    with TemporaryDirectory() as temporary_directory:
        root_path = Path(temporary_directory)
        settings = build_settings(root_path)
        service = DocumentUploadService(session=FakeSession(), settings=settings)
        fake_storage_service = FakeStorageService(
            returned_document=build_document(DocumentType.CMR),
            error_to_raise=RuntimeError("disk write failed"),
        )
        fake_logging_service = FakeApplicationLoggingService()
        service._storage_service = fake_storage_service
        service._audit_trail_service = FakeAuditTrailService()
        service._application_logging_service = fake_logging_service

        try:
            service.upload_document(
                DocumentUploadRequest(
                    delivery_slip_id=101,
                    document_type=DocumentType.CMR,
                    original_filename="cmr.pdf",
                    file_bytes=b"cmr-content",
                    uploaded_by="warehouse.user",
                    source_system="desktop_client",
                )
            )
        except RuntimeError as error:
            assert str(error) == "disk write failed"
        else:
            raise AssertionError("Expected RuntimeError when fake storage fails.")

        assert fake_logging_service.storage_failures[0]["message"] == "Document upload coordination failed."
        assert list(settings.storage.temporary_files_root.glob("*")) == []
