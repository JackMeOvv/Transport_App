"""Structured logging configuration."""

from __future__ import annotations

import logging
from logging.config import dictConfig

from logistics_app.infrastructure.config.settings import get_settings


def configure_logging(default_level: str | None = None) -> None:
    """Configure structured application logging."""
    settings = get_settings()
    resolved_level = default_level or settings.logging.level

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "structured": {
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "structured",
                    "level": resolved_level,
                }
            },
            "root": {
                "handlers": ["console"],
                "level": resolved_level,
            },
        }
    )
    logging.getLogger(__name__).debug("Structured logging configured.")
