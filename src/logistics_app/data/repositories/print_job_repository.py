"""Print job repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from logistics_app.data.models.enums import DocumentType, PrintJobStatus
from logistics_app.data.models.print_job import PrintJob


class PrintJobRepository:
    """Explicit repository for print jobs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, print_job: PrintJob) -> PrintJob:
        """Add a print job to the current unit of work."""
        self._session.add(print_job)
        return print_job

    def get_by_id(self, print_job_id: int) -> PrintJob | None:
        """Load one print job by primary key."""
        return self._session.get(PrintJob, print_job_id)

    def get_total_printed_copies(
        self,
        delivery_slip_id: int,
        document_type: DocumentType,
        split_transport_id: int | None = None,
    ) -> int:
        """Count actual printed copies for successful print jobs in one scope."""
        statement = (
            select(PrintJob)
            .where(PrintJob.delivery_slip_id == delivery_slip_id)
            .where(PrintJob.document_type == document_type)
            .where(PrintJob.status == PrintJobStatus.PRINTED)
        )
        if split_transport_id is None:
            statement = statement.where(PrintJob.split_transport_id.is_(None))
        else:
            statement = statement.where(PrintJob.split_transport_id == split_transport_id)

        total_printed = 0
        for print_job in self._session.scalars(statement):
            total_printed += print_job.printed_copy_count or 0
        return total_printed

    def list_by_delivery_slip(
        self,
        delivery_slip_id: int,
        split_transport_id: int | None = None,
    ) -> list[PrintJob]:
        """Return print jobs for one delivery scope."""
        statement = select(PrintJob).where(PrintJob.delivery_slip_id == delivery_slip_id)
        if split_transport_id is None:
            statement = statement.where(PrintJob.split_transport_id.is_(None))
        else:
            statement = statement.where(PrintJob.split_transport_id == split_transport_id)
        statement = statement.order_by(PrintJob.queued_at.desc(), PrintJob.id.desc())
        return list(self._session.scalars(statement))
