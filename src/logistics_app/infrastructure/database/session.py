"""SQLAlchemy engine and session factory setup."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from logistics_app.infrastructure.config.settings import get_settings

settings = get_settings()

engine = create_engine(
    settings.database.sqlalchemy_url,
    echo=settings.database.echo_sql,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    future=True,
)

SessionFactory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
