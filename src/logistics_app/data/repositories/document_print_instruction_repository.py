"""Document print instruction repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from logistics_app.data.models.document_print_instruction import DocumentPrintInstruction
from logistics_app.data.models.enums import DocumentType


class DocumentPrintInstructionRepository:
    """Explicit repository for print instruction records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, instruction: DocumentPrintInstruction) -> DocumentPrintInstruction:
        """Add a print instruction to the current unit of work."""
        self._session.add(instruction)
        return instruction

    def get_by_scope(
        self,
        delivery_slip_id: int,
        document_type: DocumentType,
        split_transport_id: int | None = None,
    ) -> DocumentPrintInstruction | None:
        """Fetch one instruction for a delivery scope and document type."""
        statement = (
            select(DocumentPrintInstruction)
            .where(DocumentPrintInstruction.delivery_slip_id == delivery_slip_id)
            .where(DocumentPrintInstruction.document_type == document_type)
        )
        if split_transport_id is None:
            statement = statement.where(DocumentPrintInstruction.split_transport_id.is_(None))
        else:
            statement = statement.where(
                DocumentPrintInstruction.split_transport_id == split_transport_id
            )
        return self._session.scalar(statement.limit(1))
