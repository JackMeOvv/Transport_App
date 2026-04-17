"""Helpers for structured application loggers."""

from __future__ import annotations

import logging
from typing import Any


def get_structured_logger(name: str) -> logging.Logger:
    """Return a named logger for structured application logging."""
    return logging.getLogger(name)


def bind_logger_context(logger: logging.Logger, **context: Any) -> logging.LoggerAdapter[logging.Logger]:
    """Create a logger adapter with fixed structured context fields."""
    return logging.LoggerAdapter(logger, extra=context)
