"""Document routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from logistics_app.application.services import DocumentService, DocumentUploadRequest, DocumentUploadService
from logistics_app.data.models.enums import DocumentType
from logistics_app.service_api.dependencies import get_db_session
from logistics_app.service_api.errors import raise_http_error_for_exception
from logistics_app.service_api.schemas.documents import DocumentResponse

router = APIRouter(tags=["documents"])


@router.get("/delivery-slips/{delivery_slip_id}/documents", response_model=list[DocumentResponse])
def list_documents_for_delivery(
    delivery_slip_id: int,
    pallet_id: int | None = Query(default=None),
    split_transport_id: int | None = Query(default=None),
    latest_only: bool = Query(default=True),
    session: Session = Depends(get_db_session),
) -> list[DocumentResponse]:
    """Return document metadata for a delivery scope."""
    service = DocumentService(session)
    return [
        DocumentResponse.model_validate(document)
        for document in service.list_documents_for_delivery(
            delivery_slip_id=delivery_slip_id,
            pallet_id=pallet_id,
            split_transport_id=split_transport_id,
            latest_only=latest_only,
        )
    ]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    session: Session = Depends(get_db_session),
) -> DocumentResponse:
    """Return one document metadata record."""
    service = DocumentService(session)
    try:
        return DocumentResponse.model_validate(service.get_document(document_id))
    except Exception as exception:
        raise_http_error_for_exception(exception)


@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    delivery_slip_id: int = Form(...),
    document_type: DocumentType = Form(...),
    uploaded_by: str | None = Form(default=None),
    source_system: str | None = Form(default=None),
    pallet_id: int | None = Form(default=None),
    split_transport_id: int | None = Form(default=None),
    remarks: str | None = Form(default=None),
    document_date: date | None = Form(default=None),
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> DocumentResponse:
    """Coordinate a document upload without exposing storage internals to the client."""
    service = DocumentUploadService(session)
    try:
        document = service.upload_document(
            DocumentUploadRequest(
                delivery_slip_id=delivery_slip_id,
                document_type=document_type,
                original_filename=file.filename or "",
                file_bytes=await file.read(),
                uploaded_by=uploaded_by,
                source_system=source_system,
                pallet_id=pallet_id,
                split_transport_id=split_transport_id,
                remarks=remarks,
                document_date=document_date,
            )
        )
        return DocumentResponse.model_validate(document)
    except Exception as exception:
        raise_http_error_for_exception(exception)
