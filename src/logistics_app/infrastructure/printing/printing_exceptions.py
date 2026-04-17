"""Printing exceptions."""

from __future__ import annotations


class PrintExecutionError(Exception):
    """Base exception for workstation print execution failures."""


class PrinterNotAvailableError(PrintExecutionError):
    """Raised when the selected printer cannot be found or opened."""


class PrintBackendUnavailableError(PrintExecutionError):
    """Raised when the configured workstation print backend is unavailable."""


class PrintableFileNotFoundError(PrintExecutionError):
    """Raised when the document file for printing is missing."""
