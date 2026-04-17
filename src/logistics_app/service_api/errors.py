"""Shared API error helpers."""

from __future__ import annotations

from fastapi import HTTPException, status

from logistics_app.application.services import (
    PrintConfigurationError,
    ResourceNotFoundError,
    ServiceValidationError,
)
from logistics_app.infrastructure.storage.document_storage_service import (
    DocumentFileMissingError,
    DocumentLinkValidationError,
    DocumentStorageError,
)


def raise_http_error_for_exception(exception: Exception) -> None:
    """Translate known service exceptions into HTTP responses."""
    if isinstance(exception, ResourceNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exception)) from exception
    if isinstance(
        exception,
        (
            DocumentFileMissingError,
            DocumentLinkValidationError,
            DocumentStorageError,
            ServiceValidationError,
            PrintConfigurationError,
            ValueError,
        ),
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exception)) from exception
    raise exception
