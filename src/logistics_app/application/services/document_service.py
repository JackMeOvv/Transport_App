"""Document metadata application service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from logistics_app.application.services.service_errors import ResourceNotFoundError
from logistics_app.data.models.document import Document
from logistics_app.data.repositories.document_repository import DocumentRepository


class DocumentService:
    """Provides document metadata retrieval for the API layer."""

    def __init__(self, session: Session) -> None:
        self._repository = DocumentRepository(session)

    def get_document(self, document_id: int) -> Document:
        """Return one document metadata record."""
        document = self._repository.get_by_id(document_id)
        if document is None:
            raise ResourceNotFoundError(f"Document {document_id} was not found.")
        return document

    def list_documents_for_delivery(
        self,
        delivery_slip_id: int,
        pallet_id: int | None = None,
        split_transport_id: int | None = None,
        latest_only: bool = True,
    ) -> list[Document]:
        """Return documents for a delivery, optionally scoped to pallet or split transport."""
        return self._repository.list_for_delivery(
            delivery_slip_id=delivery_slip_id,
            pallet_id=pallet_id,
            split_transport_id=split_transport_id,
            latest_only=latest_only,
        )
