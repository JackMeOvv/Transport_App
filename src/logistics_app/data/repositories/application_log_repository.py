"""Application log repository."""

from __future__ import annotations

from sqlalchemy.orm import Session

from logistics_app.data.models.application_log import ApplicationLog


class ApplicationLogRepository:
    """Explicit repository for persisted technical log records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, application_log: ApplicationLog) -> ApplicationLog:
        """Add an application log record to the current unit of work."""
        self._session.add(application_log)
        return application_log
