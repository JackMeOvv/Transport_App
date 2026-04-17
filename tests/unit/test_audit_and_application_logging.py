"""Unit tests for audit and application logging services."""

from __future__ import annotations

from dataclasses import dataclass

from logistics_app.application.services import (
    ApplicationLogContext,
    ApplicationLoggingService,
    AuditContext,
    AuditTrailService,
)
from logistics_app.data.models.application_log import ApplicationLog
from logistics_app.data.models.audit_log import AuditLog
from logistics_app.data.models.enums import (
    ApplicationLogLevel,
    AuditActionType,
    AuditEntityType,
    DocumentType,
)
from logistics_app.infrastructure.config.settings import ApplicationSettings, LoggingSettings


@dataclass
class FakeSession:
    """Minimal session test double used by logging services."""

    added_records: list[object] | None = None

    def __post_init__(self) -> None:
        if self.added_records is None:
            self.added_records = []

    def add(self, record: object) -> None:
        self.added_records.append(record)


def test_audit_trail_service_records_signed_cmr_upload() -> None:
    """Signed CMR uploads should be clearly distinguishable in the audit log."""
    session = FakeSession()
    service = AuditTrailService(session=session)

    audit_log = service.record_document_uploaded(
        document_id=15,
        document_type=DocumentType.SIGNED_CMR,
        version_number=2,
        context=AuditContext(
            performed_by="warehouse.user",
            source_system="desktop_client",
            delivery_slip_id=101,
            document_id=15,
        ),
    )

    assert isinstance(audit_log, AuditLog)
    assert audit_log.action_type == AuditActionType.UPLOAD
    assert audit_log.entity_type == AuditEntityType.DOCUMENT
    assert audit_log.details_json["event_name"] == "signed_cmr_uploaded"
    assert audit_log.details_json["version_number"] == 2


def test_audit_trail_service_records_pallet_movement() -> None:
    """Pallet movement audits should capture source and destination locations."""
    session = FakeSession()
    service = AuditTrailService(session=session)

    audit_log = service.record_pallet_moved(
        pallet_id=88,
        from_location_code="A-01-01",
        to_location_code="STAGE-02",
        context=AuditContext(
            performed_by="warehouse.user",
            source_system="desktop_client",
            delivery_slip_id=44,
            pallet_id=88,
        ),
    )

    assert audit_log.action_type == AuditActionType.MOVE
    assert audit_log.details_json["from_location_code"] == "A-01-01"
    assert audit_log.details_json["to_location_code"] == "STAGE-02"


def test_application_logging_service_persists_validation_error() -> None:
    """Validation errors should emit a warning-level persisted application log."""
    session = FakeSession()
    settings = ApplicationSettings.model_construct(logging=LoggingSettings(persist_application_logs=True))
    service = ApplicationLoggingService(
        session=session,
        logger_name="tests.validation",
        settings=settings,
    )

    service.log_validation_error(
        "Delivery slip number is missing.",
        context=ApplicationLogContext(
            acting_user="transport.user",
            request_id="req-123",
            delivery_slip_id=55,
            source_system="service_api",
            extra_data={"field_name": "delivery_slip_number"},
        ),
    )

    persisted_log = session.added_records[0]
    assert isinstance(persisted_log, ApplicationLog)
    assert persisted_log.log_level == ApplicationLogLevel.WARNING
    assert persisted_log.request_id == "req-123"
    assert persisted_log.context_json["event_name"] == "validation_error"
    assert persisted_log.context_json["field_name"] == "delivery_slip_number"


def test_application_logging_service_persists_exception_details() -> None:
    """Exceptions should store both the type and message for support diagnostics."""
    session = FakeSession()
    settings = ApplicationSettings.model_construct(logging=LoggingSettings(persist_application_logs=True))
    service = ApplicationLoggingService(
        session=session,
        logger_name="tests.errors",
        settings=settings,
    )

    try:
        raise RuntimeError("Database connection timed out.")
    except RuntimeError as error:
        service.log_database_error(
            "Could not complete database operation.",
            exception=error,
            context=ApplicationLogContext(source_system="service_api"),
        )

    persisted_log = session.added_records[0]
    assert persisted_log.log_level == ApplicationLogLevel.ERROR
    assert persisted_log.exception_type == "RuntimeError"
    assert persisted_log.exception_message == "Database connection timed out."
    assert persisted_log.context_json["event_name"] == "database_error"
