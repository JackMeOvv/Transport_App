"""Windows workstation printing backend."""

from __future__ import annotations

from pathlib import Path
from time import sleep

from logistics_app.infrastructure.printing.printing_exceptions import (
    PrintBackendUnavailableError,
    PrintExecutionError,
    PrintableFileNotFoundError,
    PrinterNotAvailableError,
)
from logistics_app.infrastructure.printing.printing_models import PrinterInfo

try:
    import win32api
    import win32print
except ImportError:  # pragma: no cover - depends on Windows runtime packages.
    win32api = None
    win32print = None


class WindowsPrintBackend:
    """Print files through the local Windows workstation.

    This implementation is intentionally isolated from business logic. It can be
    replaced later if the company standardizes on a different local print
    mechanism or a central print agent.
    """

    def list_printers(self) -> list[PrinterInfo]:
        """List printers visible on the workstation."""
        self._ensure_backend_available()
        printer_entries = win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )
        default_printer_name = self._get_default_printer_name()
        printer_infos: list[PrinterInfo] = []
        for _, _, printer_name, _ in printer_entries:
            printer_infos.append(
                PrinterInfo(
                    printer_name=printer_name,
                    is_default=printer_name == default_printer_name,
                )
            )
        return sorted(printer_infos, key=lambda printer: printer.printer_name.lower())

    def print_file(
        self,
        file_path: Path,
        printer_name: str,
        copy_count: int,
    ) -> None:
        """Send a file to a specific Windows printer using the registered file handler."""
        self._ensure_backend_available()
        if not file_path.exists() or not file_path.is_file():
            raise PrintableFileNotFoundError(f"Printable file was not found: {file_path}")
        if copy_count < 1:
            raise PrintExecutionError("At least one print copy is required.")
        self._ensure_printer_exists(printer_name)

        quoted_printer_name = f'"{printer_name}"'
        quoted_file_path = str(file_path)
        try:
            for _ in range(copy_count):
                win32api.ShellExecute(
                    0,
                    "printto",
                    quoted_file_path,
                    quoted_printer_name,
                    ".",
                    0,
                )
                sleep(0.2)
        except Exception as exc:  # pragma: no cover - depends on Windows shell integration.
            raise PrintExecutionError(
                f"Windows printing failed for printer '{printer_name}'."
            ) from exc

    def _ensure_backend_available(self) -> None:
        if win32api is None or win32print is None:
            raise PrintBackendUnavailableError(
                "The Windows printing backend is unavailable. Install pywin32 on the workstation."
            )

    def _ensure_printer_exists(self, printer_name: str) -> None:
        available_printers = {printer.printer_name for printer in self.list_printers()}
        if printer_name not in available_printers:
            raise PrinterNotAvailableError(f"Printer '{printer_name}' is not available.")

    def _get_default_printer_name(self) -> str | None:
        self._ensure_backend_available()
        try:
            return win32print.GetDefaultPrinter()
        except Exception:  # pragma: no cover - depends on Windows workstation setup.
            return None
