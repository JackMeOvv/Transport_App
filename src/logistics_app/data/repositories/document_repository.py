"""Document metadata repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from logistics_app.data.models.document import Document
from logistics_app.data.models.enums import DocumentType


class DocumentRepository:
    """Small explicit repository for document metadata operations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, document: Document) -> Document:
        """Add a document metadata record to the current unit of work."""
        self._session.add(document)
        return document

    def get_by_id(self, document_id: int) -> Document | None:
        """Load one document metadata record by primary key."""
        return self._session.get(Document, document_id)

    def get_latest_version(
        self,
        delivery_slip_id: int,
        document_type: DocumentType,
        pallet_id: int | None = None,
        split_transport_id: int | None = None,
    ) -> Document | None:
        """Return the latest document version for one business scope."""
        statement = (
            select(Document)
            .where(Document.delivery_slip_id == delivery_slip_id)
            .where(Document.document_type == document_type)
        )
        if pallet_id is None:
            statement = statement.where(Document.pallet_id.is_(None))
        else:
            statement = statement.where(Document.pallet_id == pallet_id)

        if split_transport_id is None:
            statement = statement.where(Document.split_transport_id.is_(None))
        else:
            statement = statement.where(Document.split_transport_id == split_transport_id)

        statement = statement.order_by(Document.version_number.desc()).limit(1)
        return self._session.scalar(statement)

    def list_for_delivery(
        self,
        delivery_slip_id: int,
        pallet_id: int | None = None,
        split_transport_id: int | None = None,
        latest_only: bool = True,
    ) -> list[Document]:
        """Return documents for a delivery scope."""
        statement = select(Document).where(Document.delivery_slip_id == delivery_slip_id)
        if pallet_id is not None:
            statement = statement.where(Document.pallet_id == pallet_id)

        if split_transport_id is not None:
            statement = statement.where(Document.split_transport_id == split_transport_id)

        if latest_only:
            statement = statement.where(Document.is_latest_version.is_(True))

        statement = statement.order_by(Document.document_type, Document.version_number.desc())
        return list(self._session.scalars(statement))

    def mark_existing_versions_not_latest(
        self,
        delivery_slip_id: int,
        document_type: DocumentType,
        pallet_id: int | None = None,
        split_transport_id: int | None = None,
    ) -> None:
        """Mark older versions as not latest before inserting a new version."""
        statement = select(Document).where(Document.delivery_slip_id == delivery_slip_id).where(
            Document.document_type == document_type
        )
        if pallet_id is None:
            statement = statement.where(Document.pallet_id.is_(None))
        else:
            statement = statement.where(Document.pallet_id == pallet_id)

        if split_transport_id is None:
            statement = statement.where(Document.split_transport_id.is_(None))
        else:
            statement = statement.where(Document.split_transport_id == split_transport_id)

        for existing_document in self._session.scalars(statement):
            existing_document.is_latest_version = False
