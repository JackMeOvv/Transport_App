# Internal IT Handover Guide

## Purpose

This document is intended for an internal IT team that needs to understand, operate, maintain, and later take over the application without depending on the original implementation team.

The application is designed as a Windows desktop system with a separate internal service layer:

- desktop client: Python 3.13, `PySide6`
- internal backend/service layer: `FastAPI`
- relational database: PostgreSQL
- ORM and migrations: SQLAlchemy and Alembic

The design favors explicit modules, readable business services, and externalized configuration.

## Architecture Overview

The solution is split into clear layers so responsibilities stay understandable:

- `desktop`
  Windows client screens, dialogs, reusable widgets, and theme components.
- `service_api`
  FastAPI routes, request and response schemas, and API dependency wiring.
- `application`
  Business services and use-case logic.
- `data`
  SQLAlchemy ORM models and explicit repositories.
- `infrastructure`
  Technical integrations such as configuration loading, database session setup, document storage, structured logging, and printing.
- `tests`
  Unit and integration test code.

### Architectural rule of thumb

- UI code should not contain business rules.
- API routes should stay thin and should call service classes.
- Business services should not depend on Qt or HTTP details.
- Repositories should stay focused on database access.
- Files should remain outside the database.
- Printer routing should remain configurable.

## Project Structure Explanation

Main folders:

- [src/logistics_app/desktop](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/desktop)
  Desktop application shell and reusable UI system.
- [src/logistics_app/service_api](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/service_api)
  Backend service layer used by the desktop client.
- [src/logistics_app/application/services](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/application/services)
  Readable business operations such as delivery updates, pallet movement, document upload coordination, print instructions, print jobs, and audit logging.
- [src/logistics_app/data/models](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/data/models)
  SQLAlchemy ORM models.
- [src/logistics_app/data/repositories](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/data/repositories)
  Small explicit repositories used by the service layer.
- [src/logistics_app/infrastructure](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/infrastructure)
  Configuration, database session setup, storage, printing, and logging.
- [alembic](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/alembic)
  Database migration environment and versioned migration scripts.
- [config](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/config)
  Example environment files for different environments.
- [docs](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/docs)
  Operational and technical documentation.
- [tests](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/tests)
  Automated tests.

## Database Schema Overview

The database is centered on the normal business case:

- one main delivery slip equals one delivery
- one delivery can contain multiple pallets
- one delivery can contain multiple documents
- split transport is optional and used only for exceptions

Core tables:

- `delivery_slips`
  Main delivery record.
- `pallets`
  Physical pallets or packages linked to a delivery.
- `warehouse_locations`
  Warehouse positions.
- `pallet_movements`
  Immutable movement history.
- `documents`
  Metadata for files stored outside the database.
- `document_print_instructions`
  Transport-defined print requirements.
- `print_jobs`
  Warehouse print execution requests and results.
- `audit_logs`
  Business accountability events.
- `application_logs`
  Technical support and diagnostic events.
- `split_transports`
  Lightweight optional exception structure for rare split transport cases.

For the full schema, field list, indexes, constraints, and enum overview, see [database_schema.md](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/docs/database_schema.md).

## Migration Approach

Schema changes are managed through Alembic.

Current migration structure:

- [alembic/env.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/alembic/env.py)
- [alembic/versions](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/alembic/versions)

Recommended approach for future changes:

1. Update the SQLAlchemy ORM models first.
2. Create a new Alembic revision.
3. Review the generated migration carefully before applying it.
4. Keep each migration focused on one coherent schema change.
5. Avoid editing old committed migrations that may already have been applied in other environments.

Recommended operational rule:

- treat migration scripts as an auditable deployment artifact
- apply them in order
- test them first in a non-production environment that reflects production as closely as possible

Example commands:

```powershell
c:\python314\python.exe -m alembic upgrade head
c:\python314\python.exe -m alembic current
```

## Configuration Approach

Configuration is externalized through environment variables and optional `.env` files.

Configuration entry point:

- [settings.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/infrastructure/config/settings.py)

Main configuration groups:

- `database`
- `storage`
- `printers`
- `api`
- `desktop`
- `logging`

Example configuration files:

- [config/.env.example](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/config/.env.example)
- [config/.env.development.example](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/config/.env.development.example)
- [config/.env.production.example](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/config/.env.production.example)

Detailed configuration guidance is in [configuration.md](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/docs/configuration.md).

## Storage Approach

Document binaries are stored outside PostgreSQL. The database stores only metadata.

Storage implementation:

- [document_storage_service.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/infrastructure/storage/document_storage_service.py)

Key storage rules:

- preserve the original filename in metadata
- generate a safe internal stored filename
- never silently overwrite a file
- version documents by business scope
- keep signed CMR separate from original CMR

Default storage path is controlled by:

- `LOGISTICS_APP_STORAGE__DOCUMENTS_ROOT`

Detailed storage design is in [document_storage.md](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/docs/document_storage.md).

## Printer Integration Approach

Printing is intentionally split into two layers:

- business print logic
  decides what needs to be printed, how many copies are required, and whether there are remaining copies
- workstation print execution
  sends the actual print job to a local Windows printer

Business print logic:

- [print_instruction_service.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/application/services/print_instruction_service.py)
- [print_job_service.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/application/services/print_job_service.py)

Desktop Windows print layer:

- [desktop_print_service.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/infrastructure/printing/desktop_print_service.py)
- [windows_print_backend.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/infrastructure/printing/windows_print_backend.py)

Configuration principle:

- document type maps to printer role
- printer role maps to actual printer name

This allows IT to replace or rename printers without changing business logic code.

Detailed printing guidance is in:

- [printing.md](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/docs/printing.md)
- [desktop_printing.md](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/docs/desktop_printing.md)

## Logging Approach

Two logging mechanisms are used on purpose:

- `audit_logs`
  business traceability and accountability
- `application_logs`
  technical errors and diagnostics

Audit logging is explicit. It is not attached through hidden ORM hooks.

Technical logging uses structured JSON logging and can also persist important technical failures.

Main implementation files:

- [audit_trail_service.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/application/services/audit_trail_service.py)
- [application_logging_service.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/application/services/application_logging_service.py)
- [setup.py](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/infrastructure/logging/setup.py)

Detailed guidance is in [logging_and_audit.md](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/docs/logging_and_audit.md).

## Deployment Assumptions

This codebase currently assumes:

- Windows desktop workstations for end users
- an internal network connection between the desktop client and the FastAPI backend
- PostgreSQL available on an internal server
- a filesystem location available for document storage outside the database
- Windows printers available on workstations where printing is required
- environment-specific configuration supplied by `.env` files or managed environment variables

Practical deployment model:

1. deploy the FastAPI service in the target environment
2. point it at the correct PostgreSQL server
3. configure document storage paths
4. apply Alembic migrations
5. configure printer defaults per environment
6. deploy the desktop client to Windows workstations

## Running the Application

Example backend startup:

```powershell
c:\python314\python.exe -m uvicorn logistics_app.service_api.main:app --host 0.0.0.0 --port 8000
```

Example desktop startup during development:

```powershell
c:\python314\python.exe C:/Users/bornv/OneDrive/Documenten/Transportdocuments/src/logistics_app/desktop/app.py
```

Before first startup in a new environment:

1. install Python dependencies
2. provide environment-specific configuration
3. ensure PostgreSQL is reachable
4. ensure storage paths exist or can be created
5. run Alembic migrations

## How To Move The Database To Another Environment Later

The design keeps database assumptions centralized so migration to another company-managed database environment is manageable.

Recommended process:

1. provision the new PostgreSQL server or managed PostgreSQL environment
2. create the target database and service account
3. update the database settings in environment variables or the environment-specific `.env` file
4. apply Alembic migrations to the new environment
5. move or restore business data using the company-approved database migration method
6. verify document storage paths and file access separately, because files are not stored in PostgreSQL
7. validate printer configuration separately, because printer routing is also external to the database

Important operational note:

- moving the database does not move the document files
- moving the database also does not move workstation printer configuration

Database settings to update:

- `LOGISTICS_APP_DATABASE__HOST`
- `LOGISTICS_APP_DATABASE__PORT`
- `LOGISTICS_APP_DATABASE__DATABASE_NAME`
- `LOGISTICS_APP_DATABASE__USERNAME`
- `LOGISTICS_APP_DATABASE__PASSWORD`

## How To Change Storage Paths

Update these configuration values:

- `LOGISTICS_APP_STORAGE__DOCUMENTS_ROOT`
- `LOGISTICS_APP_STORAGE__TEMPORARY_FILES_ROOT`
- `LOGISTICS_APP_STORAGE__EXPORTS_ROOT`

Recommended process:

1. prepare the new target folders
2. copy existing document files if historical documents must remain accessible
3. update the environment configuration
4. restart the backend service
5. verify that new uploads and document lookups use the new paths

Important note:

- existing `documents.storage_relative_path` values are relative to the configured documents root
- if the relative structure remains the same, moving the root path is straightforward

## How To Change Printer Defaults

Printer names and routing are controlled in configuration, not hardcoded in business logic.

To change physical default printers, update:

- `LOGISTICS_APP_PRINTERS__DEFAULTS__WAREHOUSE_MAIN_PRINTER`
- `LOGISTICS_APP_PRINTERS__DEFAULTS__LOADING_DOCK_PRINTER`
- `LOGISTICS_APP_PRINTERS__DEFAULTS__OFFICE_PRINTER`
- `LOGISTICS_APP_PRINTERS__DEFAULTS__LABEL_PRINTER`

To change which printer role is used for each document type, update:

- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__PACKING_SLIP`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__CMR`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__SIGNED_CMR`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__CERTIFICATE`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__STICKER`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__TRANSPORT_DOCUMENT`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__OTHER`

Recommended process:

1. update the printer configuration values
2. verify that the referenced printer role exists in the defaults section
3. restart the relevant service or desktop process if needed
4. test one print job for each critical document type

## Recommended Operational Ownership

For future IT ownership, the cleanest split is:

- application support
  monitors logs, validates document flows, and handles printer routing issues
- database administration
  manages PostgreSQL backups, permissions, and server migration
- infrastructure or endpoint management
  manages Windows workstation deployment, printer access, and document storage paths

## Related Documentation

- [README.md](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/README.md)
- [database_schema.md](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/docs/database_schema.md)
- [configuration.md](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/docs/configuration.md)
- [document_storage.md](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/docs/document_storage.md)
- [printing.md](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/docs/printing.md)
- [desktop_printing.md](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/docs/desktop_printing.md)
- [logging_and_audit.md](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/docs/logging_and_audit.md)
- [service_api.md](/C:/Users/bornv/OneDrive/Documenten/Transportdocuments/docs/service_api.md)
