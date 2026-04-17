# Document Storage Design

## Overview

The document storage service stores files on disk and stores only metadata in PostgreSQL.

Implementation entry point:

- [document_storage_service.py](../src/logistics_app/infrastructure/storage/document_storage_service.py)

Metadata model:

- [document.py](../src/logistics_app/data/models/document.py)

## Business Rules Covered

- Files are stored outside the database.
- The database stores only document metadata.
- The original filename is preserved in metadata.
- A separate internal storage filename is generated for safe storage.
- Files are written with exclusive create mode, so existing files are never silently overwritten.
- New uploads create new document versions instead of replacing previous metadata rows.
- Signed CMR files are stored under the `SIGNED_CMR` document type and do not overwrite `CMR` files.
- Documents can be linked to a delivery slip, and optionally to a pallet or split transport.

## Storage Layout

The default storage root is controlled by configuration:

- `LOGISTICS_APP_STORAGE__DOCUMENTS_ROOT`

Files are stored in a structured path under that root:

`<documents_root>/<delivery_slip_number>/<document_type>/[split_<split_code>/][pallet_<pallet_identifier>/]<generated_filename>`

Example:

`D:/InternalLogistics/Documents/DEL-2026-0005/signed_cmr/signed_cmr_v001_cmr_scan_<uuid>.pdf`

## Internal Filenames

Stored filenames are generated with:

- document type
- version number
- sanitized original stem
- UUID token
- safe extension when available

This ensures:

- predictable naming
- low collision risk
- no dependency on user-supplied filenames for uniqueness
- no silent overwrite of an existing file

## Metadata Stored in the Database

The `documents` table stores:

- delivery slip link
- optional pallet link
- optional split transport link
- document type
- document status
- original filename
- stored filename
- relative storage path
- mime type
- file size
- checksum
- upload metadata
- version number
- latest-version flag

## Versioning

Versioning is scoped by:

- delivery slip
- optional pallet
- optional split transport
- document type

This means:

- a second `CMR` upload for the same delivery becomes version 2 of `CMR`
- a `SIGNED_CMR` upload starts its own separate version series
- pallet-specific documents can have their own separate version chain

## Operational Note for IT

Backups and retention for physical document files must be handled at the filesystem or storage platform level, because the file binaries are intentionally kept out of PostgreSQL.
