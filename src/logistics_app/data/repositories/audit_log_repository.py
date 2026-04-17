"""Audit log repository."""

from __future__ import annotations

from sqlalchemy.orm import Session

from logistics_app.data.models.audit_log import AuditLog


class AuditLogRepository:
    """Explicit repository for business audit records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, audit_log: AuditLog) -> AuditLog:
        """Add an audit log record to the current unit of work."""
        self._session.add(audit_log)
        return audit_log
