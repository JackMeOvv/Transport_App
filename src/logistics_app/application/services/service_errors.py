"""Common application service errors."""

from __future__ import annotations


class ApplicationServiceError(Exception):
    """Base error for explicit application service failures."""


class ResourceNotFoundError(ApplicationServiceError):
    """Raised when a requested business record does not exist."""


class ServiceValidationError(ApplicationServiceError):
    """Raised when a request violates business or data validation rules."""
