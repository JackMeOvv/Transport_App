"""Document upload coordination service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from logistics_app.application.services.application_logging_service import (
    ApplicationLogContext,
    ApplicationLoggingService,
)
from logistics_app.application.services.audit_trail_service import AuditContext, AuditTrailService
from logistics_app.application.services.service_errors import ServiceValidationError
from logistics_app.data.models.document import Document
from logistics_app.data.models.enums import DocumentType
from logistics_app.infrastructure.config.settings import ApplicationSettings, get_settings
from logistics_app.infrastructure.storage.document_storage_service import (
    DocumentStorageService,
    StoreDocumentRequest,
)


@dataclass(frozen=True, slots=True)
class DocumentUploadRequest:
    """Input for coordinating a document upload from the API layer."""

    delivery_slip_id: int
    document_type: DocumentType
    original_filename: str
    file_bytes: bytes
    uploaded_by: str | None
    source_system: str | None
    pallet_id: int | None = None
    split_transport_id: int | None = None
    remarks: str | None = None
    document_date: date | None = None


class DocumentUploadService:
    """Coordinates temporary upload handling, storage, metadata, and audit logging."""

    def __init__(
        self,
        session: Session,
        settings: ApplicationSettings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._storage_service = DocumentStorageService(session, settings=self._settings)
        self._audit_trail_service = AuditTrailService(session)
        self._application_logging_service = ApplicationLoggingService(
            session=session,
            settings=self._settings,
        )

    def upload_document(self, request: DocumentUploadRequest) -> Document:
        """Store an uploaded file, persist metadata, and write audit records."""
        if not request.original_filename.strip():
            raise ServiceValidationError("The uploaded file must have a filename.")
        if not request.file_bytes:
            raise ServiceValidationError("The uploaded file is empty.")

        temporary_root = self._settings.storage.temporary_files_root
        temporary_root.mkdir(parents=True, exist_ok=True)
        temporary_file_path = temporary_root / f"upload_{uuid4().hex}_{Path(request.original_filename).name}"

        try:
            temporary_file_path.write_bytes(request.file_bytes)
            document = self._storage_service.store_document(
                StoreDocumentRequest(
                    delivery_slip_id=request.delivery_slip_id,
                    document_type=request.document_type,
                    source_file_path=temporary_file_path,
                    uploaded_by=request.uploaded_by,
                    pallet_id=request.pallet_id,
                    split_transport_id=request.split_transport_id,
                    remarks=request.remarks,
                    document_date=request.document_date,
                )
            )
            self._audit_trail_service.record_document_uploaded(
                document_id=document.id,
                document_type=document.document_type,
                version_number=document.version_number,
                context=AuditContext(
                    performed_by=request.uploaded_by,
                    source_system=request.source_system,
                    delivery_slip_id=document.delivery_slip_id,
                    pallet_id=document.pallet_id,
                    document_id=document.id,
                    split_transport_id=document.split_transport_id,
                ),
            )
            return document
        except Exception as exception:
            self._application_logging_service.log_storage_failure(
                message="Document upload coordination failed.",
                exception=exception,
                context=ApplicationLogContext(
                    acting_user=request.uploaded_by,
                    delivery_slip_id=request.delivery_slip_id,
                    source_system=request.source_system,
                    extra_data={
                        "event_name": "document_upload_failed",
                        "document_type": request.document_type.value,
                        "original_filename": request.original_filename,
                    },
                ),
            )
            raise
        finally:
            if temporary_file_path.exists():
                temporary_file_path.unlink()
