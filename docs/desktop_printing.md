# Desktop Printing Layer

## Overview

The desktop client now has a workstation-oriented print execution layer under [infrastructure/printing](../src/logistics_app/infrastructure/printing).

This layer keeps two responsibilities separate:

- business logic decides what should be printed and how many copies are required
- the desktop workstation executes the actual local print action

## Main Components

- [desktop_print_service.py](../src/logistics_app/infrastructure/printing/desktop_print_service.py)
  Coordinates local print execution with `print_jobs` tracking.
- [windows_print_backend.py](../src/logistics_app/infrastructure/printing/windows_print_backend.py)
  Windows-specific backend for local workstation printing.
- [workstation_print_backend.py](../src/logistics_app/infrastructure/printing/workstation_print_backend.py)
  Backend contract that keeps the desktop print service decoupled from one implementation.
- [printing_models.py](../src/logistics_app/infrastructure/printing/printing_models.py)
  Shared request and result models.
- [printing_exceptions.py](../src/logistics_app/infrastructure/printing/printing_exceptions.py)
  Explicit printing errors for readable failure handling.

## How It Works

1. Transport or warehouse logic creates a print job through the business service layer.
2. The desktop print service requests local execution for that print job.
3. The service marks the job as sent.
4. The Windows backend sends the file to the selected workstation printer.
5. The service marks the print job as printed or failed.
6. Failures are reported back into `print_jobs` and technical logging.

## Windows Support

The current workstation implementation uses `pywin32`.

It supports:

- listing visible Windows printers
- printing to a selected Windows printer
- multiple copies by repeated workstation print submission
- reprints through the existing `print_jobs` flow

If a different workstation print mechanism is needed later, it can replace the backend without changing the business layer.

## Architectural Boundary

This design intentionally avoids coupling business logic to one physical printer setup.

The business layer works with:

- document types
- required copies
- printer roles
- optional manual printer overrides

The desktop layer resolves those into actual workstation printer names and executes the local print action.
