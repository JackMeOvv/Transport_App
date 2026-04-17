# Internal Logistics Desktop Application

## Purpose

This repository contains the initial project structure for a production-oriented internal logistics system for transport and warehouse operations.

The solution is intentionally organized for long-term maintainability:

- A Windows desktop client will be built with `PySide6`.
- A backend service layer will be built with `FastAPI`.
- Business logic is separated from UI, storage, printing, and database concerns.
- PostgreSQL is the target relational database.
- SQLAlchemy and Alembic are used so schema changes remain explicit and controlled.

## Architecture Overview

The structure follows a layered approach so an internal IT team can quickly understand where responsibilities belong:

- `desktop`
  Contains the Windows client application, including screens, dialogs, reusable widgets, and theme assets. The application supports a role-based workflow where the warehouse initiates Delivery Note generation and pallet movement, while transport focuses on document completeness and readiness confirmation.
- `service_api`
  Contains the FastAPI service layer that exposes application functionality over the internal network.
- `application`
  Contains use-case oriented services and orchestration logic.
- `domain`
  Contains business concepts, rules, and domain-level types that should stay independent from UI and infrastructure.
- `data`
  Contains SQLAlchemy ORM models and repository implementations.
- `infrastructure`
  Contains technical integrations such as database setup, file storage, structured logging, printing, and configuration loading.
- `tests`
  Contains automated tests grouped by application area.

This separation is deliberate:

- UI code should not contain business rules.
- Business rules should not depend on Qt widgets or HTTP route handlers.
- Database and file storage details should stay behind dedicated infrastructure and repository layers.
- Printing and document storage are treated as operational capabilities, not embedded inside screen code.

## Why This Structure Was Chosen

This application must support future internal handover and possible migration into a company-managed environment. For that reason, the project favors:

- clear names over short names
- explicit modules over mixed responsibilities
- standard Python package layout
- database portability at the schema and ORM level
- externalized configuration
- a clear place for operational concerns such as logging, printing, and file storage

## Configuration

Application configuration is externalized through environment variables and optional `.env` files.

- Database host, port, database name, username, and password are externalized.
- Document storage and export paths are externalized.
- Default printer mappings are externalized by operational role.
- Environment-specific values can be changed without code changes.

Configuration examples are available in [config](config), and the handover guide is in [docs/configuration.md](docs/configuration.md).

Document storage behavior is documented in [docs/document_storage.md](docs/document_storage.md).

Logging and audit behavior is documented in [docs/logging_and_audit.md](docs/logging_and_audit.md).

Printing behavior is documented in [docs/printing.md](docs/printing.md).

Desktop workstation printing is documented in [docs/desktop_printing.md](docs/desktop_printing.md).

The reusable desktop design system lives under [src/logistics_app/desktop/ui](src/logistics_app/desktop/ui) and can be previewed through [app.py](src/logistics_app/desktop/app.py).

## Initial Status

This commit provides the project skeleton and starter configuration only. The next implementation steps would typically be:

1. Define core domain entities such as deliveries, pallets, warehouse locations, and documents.
2. Add SQLAlchemy models and the first Alembic migration.
3. Build the FastAPI app startup and dependency wiring.
4. Build the PySide6 desktop shell and shared design system.
5. Add structured logging, document storage conventions, and printer integration contracts.
