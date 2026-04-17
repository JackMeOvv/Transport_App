"""Backend contract for workstation-based printing."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from logistics_app.infrastructure.printing.printing_models import PrinterInfo


class WorkstationPrintBackend(Protocol):
    """Protocol implemented by workstation print backends."""

    def list_printers(self) -> list[PrinterInfo]:
        """Return printers visible on the local Windows workstation."""

    def print_file(
        self,
        file_path: Path,
        printer_name: str,
        copy_count: int,
    ) -> None:
        """Send a file to a Windows printer."""
