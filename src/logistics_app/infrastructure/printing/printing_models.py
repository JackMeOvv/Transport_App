"""Shared models for workstation-based printing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from logistics_app.application.services.print_job_service import PrintRequest


@dataclass(frozen=True, slots=True)
class PrinterInfo:
    """Basic Windows printer details exposed to the desktop client."""

    printer_name: str
    is_default: bool = False


@dataclass(frozen=True, slots=True)
class DesktopPrintExecutionRequest:
    """Input for requesting and executing a workstation print."""

    print_request: PrintRequest
    document_file_path: Path


@dataclass(frozen=True, slots=True)
class DesktopReprintExecutionRequest:
    """Input for requesting and executing a workstation reprint."""

    original_print_job_id: int
    document_file_path: Path
    requested_by: str | None
    source_system: str | None
    requested_copy_count: int | None = None
    printer_name_override: str | None = None


@dataclass(frozen=True, slots=True)
class PrintExecutionResult:
    """Outcome of one workstation print execution attempt."""

    print_job_id: int
    printer_name: str
    requested_copy_count: int
    printed_copy_count: int
    succeeded: bool
    error_message: str | None = None
