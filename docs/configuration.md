# Configuration Guide

## Overview

The application uses environment-based configuration. This keeps secrets out of source code and allows the same codebase to move between development, test, staging, and production environments.

Configuration is loaded by [settings.py](../src/logistics_app/infrastructure/config/settings.py) through the `LOGISTICS_APP_` environment variable prefix.

The project also includes example configuration files in [config](../config):

- [.env.example](../config/.env.example)
- [.env.development.example](../config/.env.development.example)
- [.env.production.example](../config/.env.production.example)

## How Configuration Is Structured

Settings are grouped by responsibility:

- `database`
  Database server, database name, user, password, and connection pool settings.
- `storage`
  Root paths for documents, temporary files, and exports.
- `printers`
  Printer backend behavior, default printer names for operational roles, and default printer routing by document type.
- `api`
  Internal FastAPI service address and request timeout settings.
- `desktop`
  Desktop client presentation defaults.
- `logging`
  Log level and persisted application logging behavior.

Nested values use a double underscore in environment variable names.

Examples:

- `LOGISTICS_APP_DATABASE__HOST`
- `LOGISTICS_APP_STORAGE__DOCUMENTS_ROOT`
- `LOGISTICS_APP_PRINTERS__DEFAULTS__WAREHOUSE_MAIN_PRINTER`

## Running the Application

### Option 1: Local `.env` file

1. Copy [config/.env.example](../config/.env.example) to `.env` in the repository root.
2. Replace placeholder values with environment-appropriate values.
3. Start the service or desktop process from the repository root.

Important:

- Do not commit the real `.env` file to source control.
- Store production passwords in a company-managed secret store when available.

### Option 2: Environment variables managed by IT

In controlled environments, IT can define the same settings directly as environment variables instead of using a local `.env` file.

This is the preferred long-term production approach.

## Moving to Another Environment

To move the application to another environment:

1. Keep the same codebase.
2. Provide a new environment-specific `.env` file or managed environment variables.
3. Update the database server values under the `database` section.
4. Update document and export paths under the `storage` section.
5. Update printer defaults under the `printers` section.
6. Update service URL settings under the `api` section if the API host changes.

No code changes should be required for those environment moves.

## Pointing to Another Database Server

Update these values:

- `LOGISTICS_APP_DATABASE__HOST`
- `LOGISTICS_APP_DATABASE__PORT`
- `LOGISTICS_APP_DATABASE__DATABASE_NAME`
- `LOGISTICS_APP_DATABASE__USERNAME`
- `LOGISTICS_APP_DATABASE__PASSWORD`

The SQLAlchemy connection string is assembled from those values in code. That keeps the config explicit and easier for IT to review.

## Changing Storage Paths

Update these values:

- `LOGISTICS_APP_STORAGE__DOCUMENTS_ROOT`
- `LOGISTICS_APP_STORAGE__TEMPORARY_FILES_ROOT`
- `LOGISTICS_APP_STORAGE__EXPORTS_ROOT`

Recommended practice:

- Use managed storage locations that are backed up according to company policy.
- Keep document storage outside PostgreSQL.
- Use absolute paths in Windows environments.

## Reconfiguring Printer Defaults

Update these values:

- `LOGISTICS_APP_PRINTERS__DEFAULTS__WAREHOUSE_MAIN_PRINTER`
- `LOGISTICS_APP_PRINTERS__DEFAULTS__LOADING_DOCK_PRINTER`
- `LOGISTICS_APP_PRINTERS__DEFAULTS__OFFICE_PRINTER`
- `LOGISTICS_APP_PRINTERS__DEFAULTS__LABEL_PRINTER`

If document-type routing needs to change, update these values as well:

- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__PACKING_SLIP`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__CMR`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__SIGNED_CMR`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__CERTIFICATE`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__STICKER`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__TRANSPORT_DOCUMENT`
- `LOGISTICS_APP_PRINTERS__DOCUMENT_TYPE_MAPPING__OTHER`

Also review:

- `LOGISTICS_APP_PRINTERS__SPOOLER_BACKEND`
- `LOGISTICS_APP_PRINTERS__JOB_TIMEOUT_SECONDS`
- `LOGISTICS_APP_PRINTERS__ALLOW_DIRECT_PRINT`

The application should refer to printer roles in business logic and screens, while the actual printer names remain configurable.

## Secret Handling

Do not hardcode:

- database passwords
- service credentials
- environment-specific internal server names

Use:

- environment variables
- a `.env` file outside source control for local setup
- company-managed secret tooling in controlled environments when available

## Example: Minimal Database Override

```env
LOGISTICS_APP_DATABASE__HOST=db-prod.internal
LOGISTICS_APP_DATABASE__DATABASE_NAME=logistics_app
LOGISTICS_APP_DATABASE__USERNAME=logistics_service
LOGISTICS_APP_DATABASE__PASSWORD=replace_with_secret
```

## Example: Minimal Storage and Printer Override

```env
LOGISTICS_APP_STORAGE__DOCUMENTS_ROOT=D:/InternalLogistics/Documents
LOGISTICS_APP_STORAGE__EXPORTS_ROOT=D:/InternalLogistics/Exports
LOGISTICS_APP_PRINTERS__DEFAULTS__WAREHOUSE_MAIN_PRINTER=Warehouse_Main_01
LOGISTICS_APP_PRINTERS__DEFAULTS__LABEL_PRINTER=Warehouse_Label_01
```

## Notes for Internal IT

- The code expects configuration to be externalized and environment-specific.
- The nested settings structure is intended to remain readable rather than clever.
- If company standards later require configuration from another provider, the replacement should happen inside the configuration layer only, without spreading environment handling across the application.
