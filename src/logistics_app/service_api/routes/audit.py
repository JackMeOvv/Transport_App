"""Audit routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from logistics_app.application.services import AuditContext, AuditTrailService
from logistics_app.service_api.dependencies import get_db_session
from logistics_app.service_api.schemas.audit import AuditLogResponse, AuditLogWriteRequest

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.post("", response_model=AuditLogResponse)
def write_audit_log(
    request: AuditLogWriteRequest,
    session: Session = Depends(get_db_session),
) -> AuditLogResponse:
    """Write an explicit business audit log entry through the service layer."""
    service = AuditTrailService(session)
    audit_log = service.record_custom_event(
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        action_type=request.action_type,
        context=AuditContext(
            performed_by=request.performed_by,
            source_system=request.source_system,
            delivery_slip_id=request.delivery_slip_id,
            pallet_id=request.pallet_id,
            document_id=request.document_id,
            split_transport_id=request.split_transport_id,
        ),
        details=request.details,
    )
    return AuditLogResponse.model_validate(audit_log)
