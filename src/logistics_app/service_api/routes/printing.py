"""Printing routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from logistics_app.application.services import (
    PrintInstructionService,
    PrintJobService,
    PrintRequest,
)
from logistics_app.data.models.enums import DocumentType
from logistics_app.service_api.dependencies import get_db_session
from logistics_app.service_api.errors import raise_http_error_for_exception
from logistics_app.service_api.schemas.printing import (
    PrintInstructionResponse,
    PrintInstructionUpsertRequest,
    PrintJobFailedRequest,
    PrintJobPrintedRequest,
    PrintJobReprintRequest,
    PrintJobRequestSchema,
    PrintJobResponse,
    PrintRequirementSummaryResponse,
)

router = APIRouter(tags=["printing"])


@router.get(
    "/delivery-slips/{delivery_slip_id}/print-instructions",
    response_model=list[PrintInstructionResponse],
)
def list_print_instructions(
    delivery_slip_id: int,
    split_transport_id: int | None = None,
    session: Session = Depends(get_db_session),
) -> list[PrintInstructionResponse]:
    """Return transport-defined print instructions for a delivery scope."""
    service = PrintInstructionService(session)
    return [
        PrintInstructionResponse.model_validate(instruction)
        for instruction in service.list_instructions(
            delivery_slip_id=delivery_slip_id,
            split_transport_id=split_transport_id,
        )
    ]


@router.put(
    "/delivery-slips/{delivery_slip_id}/print-instructions/{document_type}",
    response_model=PrintInstructionResponse,
)
def upsert_print_instruction(
    delivery_slip_id: int,
    document_type: DocumentType,
    request: PrintInstructionUpsertRequest,
    session: Session = Depends(get_db_session),
) -> PrintInstructionResponse:
    """Create or update required print copies for one document type."""
    service = PrintInstructionService(session)
    try:
        instruction = service.upsert_instruction(
            delivery_slip_id=delivery_slip_id,
            document_type=document_type,
            required_copy_count=request.required_copy_count,
            changed_by=request.changed_by,
            source_system=request.source_system,
            split_transport_id=request.split_transport_id,
            printer_role=request.printer_role,
            is_mandatory=request.is_mandatory,
            notes=request.notes,
        )
        return PrintInstructionResponse.model_validate(instruction)
    except Exception as exception:
        raise_http_error_for_exception(exception)


@router.get(
    "/delivery-slips/{delivery_slip_id}/print-summary/{document_type}",
    response_model=PrintRequirementSummaryResponse,
)
def get_print_requirement_summary(
    delivery_slip_id: int,
    document_type: DocumentType,
    split_transport_id: int | None = None,
    session: Session = Depends(get_db_session),
) -> PrintRequirementSummaryResponse:
    """Return required, printed, and remaining copies."""
    service = PrintInstructionService(session)
    summary = service.get_requirement_summary(
        delivery_slip_id=delivery_slip_id,
        document_type=document_type,
        split_transport_id=split_transport_id,
    )
    return PrintRequirementSummaryResponse.model_validate(summary.__dict__)


@router.get("/delivery-slips/{delivery_slip_id}/print-jobs", response_model=list[PrintJobResponse])
def list_print_jobs(
    delivery_slip_id: int,
    split_transport_id: int | None = None,
    session: Session = Depends(get_db_session),
) -> list[PrintJobResponse]:
    """Return print jobs for a delivery scope."""
    service = PrintJobService(session)
    return [
        PrintJobResponse.model_validate(print_job)
        for print_job in service.list_jobs(
            delivery_slip_id=delivery_slip_id,
            split_transport_id=split_transport_id,
        )
    ]


@router.post("/print-jobs", response_model=PrintJobResponse)
def request_print_job(
    request: PrintJobRequestSchema,
    session: Session = Depends(get_db_session),
) -> PrintJobResponse:
    """Create a new print job request."""
    service = PrintJobService(session)
    try:
        print_job, _summary = service.request_print(
            PrintRequest(
                delivery_slip_id=request.delivery_slip_id,
                document_type=request.document_type,
                requested_by=request.requested_by,
                source_system=request.source_system,
                document_id=request.document_id,
                split_transport_id=request.split_transport_id,
                printer_name_override=request.printer_name_override,
                requested_copy_count=request.requested_copy_count,
            )
        )
        return PrintJobResponse.model_validate(print_job)
    except Exception as exception:
        raise_http_error_for_exception(exception)


@router.post("/print-jobs/{print_job_id}/reprint", response_model=PrintJobResponse)
def request_reprint_job(
    print_job_id: int,
    request: PrintJobReprintRequest,
    session: Session = Depends(get_db_session),
) -> PrintJobResponse:
    """Create a reprint job from an existing job."""
    service = PrintJobService(session)
    try:
        print_job = service.request_reprint(
            print_job_id=print_job_id,
            requested_by=request.requested_by,
            source_system=request.source_system,
            requested_copy_count=request.requested_copy_count,
            printer_name_override=request.printer_name_override,
        )
        return PrintJobResponse.model_validate(print_job)
    except Exception as exception:
        raise_http_error_for_exception(exception)


@router.post("/print-jobs/{print_job_id}/mark-sent", response_model=PrintJobResponse)
def mark_print_job_sent(
    print_job_id: int,
    session: Session = Depends(get_db_session),
) -> PrintJobResponse:
    """Mark a print job as sent to the printer subsystem."""
    service = PrintJobService(session)
    try:
        return PrintJobResponse.model_validate(service.mark_job_sent(print_job_id))
    except Exception as exception:
        raise_http_error_for_exception(exception)


@router.post("/print-jobs/{print_job_id}/mark-printed", response_model=PrintJobResponse)
def mark_print_job_printed(
    print_job_id: int,
    request: PrintJobPrintedRequest,
    session: Session = Depends(get_db_session),
) -> PrintJobResponse:
    """Mark a print job as successfully printed."""
    service = PrintJobService(session)
    try:
        return PrintJobResponse.model_validate(
            service.mark_job_printed(
                print_job_id=print_job_id,
                printed_copy_count=request.printed_copy_count,
            )
        )
    except Exception as exception:
        raise_http_error_for_exception(exception)


@router.post("/print-jobs/{print_job_id}/mark-failed", response_model=PrintJobResponse)
def mark_print_job_failed(
    print_job_id: int,
    request: PrintJobFailedRequest,
    session: Session = Depends(get_db_session),
) -> PrintJobResponse:
    """Mark a print job as failed."""
    service = PrintJobService(session)
    try:
        return PrintJobResponse.model_validate(
            service.mark_job_failed(
                print_job_id=print_job_id,
                error_message=request.error_message,
                source_system=request.source_system,
            )
        )
    except Exception as exception:
        raise_http_error_for_exception(exception)
