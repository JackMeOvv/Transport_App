"""FastAPI dependency helpers."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from logistics_app.infrastructure.config.settings import ApplicationSettings, get_settings
from logistics_app.infrastructure.database.session import SessionFactory


def get_application_settings() -> ApplicationSettings:
    """Return shared application settings."""
    return get_settings()


def get_db_session() -> Generator[Session, None, None]:
    """Provide one SQLAlchemy session per request."""
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
