"""Document API schemas."""

from __future__ import annotations

from datetime import date, datetime

from logistics_app.data.models.enums import DocumentStatus, DocumentType
from logistics_app.service_api.schemas.common import OrmResponseModel


class DocumentResponse(OrmResponseModel):
    id: int
    delivery_slip_id: int
    pallet_id: int | None
    split_transport_id: int | None
    document_type: DocumentType
    document_status: DocumentStatus
    original_filename: str | None
    stored_filename: str | None
    storage_relative_path: str | None
    mime_type: str | None
    file_size_bytes: int | None
    checksum_sha256: str | None
    uploaded_at: datetime | None
    uploaded_by: str | None
    document_date: date | None
    version_number: int
    is_latest_version: bool
    remarks: str | None
