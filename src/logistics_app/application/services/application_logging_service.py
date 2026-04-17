"""Technical application logging support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import logging
from typing import Any

from sqlalchemy.orm import Session

from logistics_app.data.models.application_log import ApplicationLog
from logistics_app.data.models.enums import ApplicationLogLevel
from logistics_app.data.repositories.application_log_repository import ApplicationLogRepository
from logistics_app.infrastructure.config.settings import ApplicationSettings, get_settings


@dataclass(frozen=True, slots=True)
class ApplicationLogContext:
    """Optional business and request context for a technical log event."""

    acting_user: str | None = None
    request_id: str | None = None
    delivery_slip_id: int | None = None
    pallet_id: int | None = None
    document_id: int | None = None
    source_system: str | None = None
    extra_data: dict[str, Any] | None = None


class ApplicationLoggingService:
    """Emits structured application logs and optionally persists them.

    Callers use this service deliberately for important technical events such as
    exceptions, database failures, storage failures, print failures, and
    validation problems. No automatic persistence is hidden behind unrelated
    code paths.
    """

    def __init__(
        self,
        session: Session | None = None,
        logger_name: str | None = None,
        settings: ApplicationSettings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        resolved_logger_name = logger_name or self._settings.logging.application_logger_name
        self._logger = logging.getLogger(resolved_logger_name)
        self._repository = ApplicationLogRepository(session) if session is not None else None

    def log_exception(
        self,
        message: str,
        exception: Exception,
        context: ApplicationLogContext | None = None,
    ) -> None:
        """Log an unexpected exception."""
        self._write_log(
            log_level=ApplicationLogLevel.ERROR,
            message=message,
            context=context,
            exception=exception,
            event_name="exception",
        )

    def log_database_error(
        self,
        message: str,
        exception: Exception,
        context: ApplicationLogContext | None = None,
    ) -> None:
        """Log a database-related error."""
        self._write_log(
            log_level=ApplicationLogLevel.ERROR,
            message=message,
            context=context,
            exception=exception,
            event_name="database_error",
        )

    def log_storage_failure(
        self,
        message: str,
        exception: Exception,
        context: ApplicationLogContext | None = None,
    ) -> None:
        """Log a document storage failure."""
        self._write_log(
            log_level=ApplicationLogLevel.ERROR,
            message=message,
            context=context,
            exception=exception,
            event_name="storage_failure",
        )

    def log_print_failure(
        self,
        message: str,
        exception: Exception | None = None,
        context: ApplicationLogContext | None = None,
    ) -> None:
        """Log a print-related failure."""
        self._write_log(
            log_level=ApplicationLogLevel.ERROR,
            message=message,
            context=context,
            exception=exception,
            event_name="print_failure",
        )

    def log_validation_error(
        self,
        message: str,
        context: ApplicationLogContext | None = None,
    ) -> None:
        """Log a validation error."""
        self._write_log(
            log_level=ApplicationLogLevel.WARNING,
            message=message,
            context=context,
            exception=None,
            event_name="validation_error",
        )

    def log_info(
        self,
        message: str,
        context: ApplicationLogContext | None = None,
    ) -> None:
        """Log a structured informational event."""
        self._write_log(
            log_level=ApplicationLogLevel.INFO,
            message=message,
            context=context,
            exception=None,
            event_name="application_event",
        )

    def _write_log(
        self,
        log_level: ApplicationLogLevel,
        message: str,
        context: ApplicationLogContext | None,
        exception: Exception | None,
        event_name: str,
    ) -> None:
        context = context or ApplicationLogContext()
        context_json = self._build_context_json(event_name=event_name, context=context)

        self._emit_structured_log(
            log_level=log_level,
            message=message,
            exception=exception,
            context=context,
            context_json=context_json,
        )
        self._persist_application_log(
            log_level=log_level,
            message=message,
            exception=exception,
            context=context,
            context_json=context_json,
        )

    def _emit_structured_log(
        self,
        log_level: ApplicationLogLevel,
        message: str,
        exception: Exception | None,
        context: ApplicationLogContext,
        context_json: dict[str, Any],
    ) -> None:
        log_method = getattr(self._logger, log_level.value.lower())
        extra = {
            "request_id": context.request_id,
            "acting_user": context.acting_user,
            "delivery_slip_id": context.delivery_slip_id,
            "pallet_id": context.pallet_id,
            "document_id": context.document_id,
            "source_system": context.source_system,
            "context_json": context_json,
        }
        if exception is None:
            log_method(message, extra=extra)
        else:
            log_method(message, extra=extra, exc_info=exception)

    def _persist_application_log(
        self,
        log_level: ApplicationLogLevel,
        message: str,
        exception: Exception | None,
        context: ApplicationLogContext,
        context_json: dict[str, Any],
    ) -> None:
        if not self._settings.logging.persist_application_logs or self._repository is None:
            return

        application_log = ApplicationLog(
            logged_at=datetime.now(UTC),
            log_level=log_level,
            logger_name=self._logger.name,
            message=message,
            exception_type=type(exception).__name__ if exception is not None else None,
            exception_message=str(exception) if exception is not None else None,
            context_json=context_json,
            delivery_slip_id=context.delivery_slip_id,
            pallet_id=context.pallet_id,
            document_id=context.document_id,
            request_id=context.request_id,
        )
        self._repository.add(application_log)

    def _build_context_json(
        self,
        event_name: str,
        context: ApplicationLogContext,
    ) -> dict[str, Any]:
        context_json: dict[str, Any] = {
            "event_name": event_name,
            "acting_user": context.acting_user,
            "source_system": context.source_system,
        }
        if context.extra_data:
            context_json.update(context.extra_data)
        return context_json
