"""Printing API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from logistics_app.data.models.enums import DocumentType, PrintJobStatus, PrintTargetType
from logistics_app.service_api.schemas.common import OrmResponseModel


class PrintInstructionUpsertRequest(BaseModel):
    required_copy_count: int
    changed_by: str | None = None
    source_system: str | None = None
    split_transport_id: int | None = None
    printer_role: str | None = None
    is_mandatory: bool = True
    notes: str | None = None


class PrintInstructionResponse(OrmResponseModel):
    id: int
    delivery_slip_id: int
    split_transport_id: int | None
    document_type: DocumentType
    required_copy_count: int
    printer_role: str | None
    is_mandatory: bool
    notes: str | None
    updated_at: datetime
    updated_by: str | None


class PrintRequirementSummaryResponse(BaseModel):
    delivery_slip_id: int
    document_type: DocumentType
    split_transport_id: int | None
    required_copy_count: int
    printed_copy_count: int
    remaining_copy_count: int
    printer_role: str | None
    is_mandatory: bool


class PrintJobRequestSchema(BaseModel):
    delivery_slip_id: int
    document_type: DocumentType
    requested_by: str | None = None
    source_system: str | None = None
    document_id: int | None = None
    split_transport_id: int | None = None
    printer_name_override: str | None = None
    requested_copy_count: int | None = None


class PrintJobReprintRequest(BaseModel):
    requested_by: str | None = None
    source_system: str | None = None
    requested_copy_count: int | None = None
    printer_name_override: str | None = None


class PrintJobPrintedRequest(BaseModel):
    printed_copy_count: int


class PrintJobFailedRequest(BaseModel):
    error_message: str
    source_system: str | None = None


class PrintJobResponse(OrmResponseModel):
    id: int
    delivery_slip_id: int | None
    document_id: int | None
    document_type: DocumentType
    split_transport_id: int | None
    target_type: PrintTargetType
    printer_role: str | None
    printer_name: str
    is_manual_printer_override: bool
    requested_copy_count: int
    printed_copy_count: int | None
    reprint_of_print_job_id: int | None
    status: PrintJobStatus
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    requested_by: str | None
    error_message: str | None
