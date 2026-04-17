# PostgreSQL Database Schema Design

## Design Goals

This schema is designed around the normal business flow:

- One delivery slip equals one delivery.
- A delivery usually moves as one transport flow.
- A delivery can contain multiple pallets.
- A delivery can have multiple operational documents.
- Warehouse tracking focuses on location and pallet movement history.
- Transport is the source of truth for required delivery documents and print copy counts.

Rare split transport cases are supported, but kept optional so the common workflow remains simple.

## General Design Principles

- Use surrogate primary keys with `bigint` identity columns for operational tables.
- Use explicit foreign keys and standard relational constraints.
- Keep files outside the database; store only metadata and file references.
- Use PostgreSQL-friendly types, but avoid overly database-specific patterns so future migration remains manageable.
- Use UTC timestamps with `timestamp with time zone`.
- Use clear status enums for readability and consistency.
- Use `created_at` and `updated_at` consistently where record lifecycle tracking matters.

## Recommended PostgreSQL Enums

These enums improve readability but remain simple enough to replace with lookup tables later if required by company standards.

### `document_type`

- `PACKING_SLIP`
- `CMR`
- `SIGNED_CMR`
- `CERTIFICATE`
- `STICKER`
- `TRANSPORT_DOCUMENT`
- `OTHER`

### `document_status`

- `EXPECTED`
- `AVAILABLE`
- `MISSING`
- `SUPERSEDED`
- `ARCHIVED`

### `pallet_status`

- `REGISTERED`
- `IN_WAREHOUSE`
- `STAGED`
- `LOADED`
- `DISPATCHED`
- `DELIVERED`
- `LOST`
- `DAMAGED`

### `warehouse_location_type`

- `RECEIVING`
- `STORAGE`
- `STAGING`
- `LOADING_DOCK`
- `QUARANTINE`
- `OUTBOUND_BUFFER`

### `pallet_movement_type`

- `RECEIVED`
- `PUT_AWAY`
- `RELOCATED`
- `STAGED_FOR_LOADING`
- `LOADED`
- `UNLOADED`
- `CORRECTED`

### `print_target_type`

- `DELIVERY`
- `DOCUMENT`
- `SPLIT_TRANSPORT`

### `print_job_status`

- `QUEUED`
- `SENT`
- `PRINTED`
- `FAILED`
- `CANCELLED`

### `audit_entity_type`

- `DELIVERY_SLIP`
- `PALLET`
- `WAREHOUSE_LOCATION`
- `DOCUMENT`
- `PRINT_JOB`
- `SPLIT_TRANSPORT`
- `SYSTEM`

### `audit_action_type`

- `CREATE`
- `UPDATE`
- `DELETE`
- `STATUS_CHANGE`
- `PRINT`
- `UPLOAD`
- `MOVE`
- `LOAD`
- `UNLOAD`
- `LOGIN`
- `LOGOUT`

### `application_log_level`

- `DEBUG`
- `INFO`
- `WARNING`
- `ERROR`
- `CRITICAL`

## Core Tables

### `delivery_slips`

Main operational record. One row represents one delivery.

| Field | Type | Null | Notes |
|---|---|---:|---|
| `id` | `bigint` | No | Primary key |
| `delivery_slip_number` | `varchar(50)` | No | Business-visible unique delivery slip reference |
| `customer_reference` | `varchar(100)` | Yes | External customer reference |
| `customer_name` | `varchar(200)` | Yes | Useful denormalized operational value |
| `delivery_date` | `date` | Yes | Planned or agreed delivery date |
| `origin_name` | `varchar(200)` | Yes | Operational origin label |
| `destination_name` | `varchar(200)` | Yes | Operational destination label |
| `transport_reference` | `varchar(100)` | Yes | Transport planning or TMS reference |
| `status` | `varchar(50)` or enum | No | Recommended values managed consistently in app |
| `is_split_transport` | `boolean` | No | Default `false`; indicates rare split case exists |
| `notes` | `text` | Yes | Business notes |
| `created_at` | `timestamptz` | No | Default current timestamp |
| `created_by` | `varchar(100)` | Yes | User or service account |
| `updated_at` | `timestamptz` | No | Default current timestamp |
| `updated_by` | `varchar(100)` | Yes | User or service account |

Primary key:

- `pk_delivery_slips (id)`

Recommended indexes:

- unique index on `delivery_slip_number`
- index on `transport_reference`
- index on `delivery_date`
- index on `status`
- index on `is_split_transport`

Recommended constraints:

- `delivery_slip_number` must not be blank
- `status` must not be blank

Recommended check constraints:

- `char_length(trim(delivery_slip_number)) > 0`
- `char_length(trim(status)) > 0`

### `pallets`

Represents physical pallets or package units belonging to a delivery.

| Field | Type | Null | Notes |
|---|---|---:|---|
| `id` | `bigint` | No | Primary key |
| `delivery_slip_id` | `bigint` | No | FK to `delivery_slips.id` |
| `pallet_identifier` | `varchar(100)` | No | Unique pallet ID visible to operations |
| `split_transport_id` | `bigint` | Yes | Optional FK for rare split assignment |
| `current_warehouse_location_id` | `bigint` | Yes | FK to latest known warehouse location |
| `status` | `pallet_status` | No | Operational pallet state |
| `gross_weight_kg` | `numeric(12,3)` | Yes | Optional weight |
| `package_count` | `integer` | Yes | Optional package count inside pallet |
| `description` | `varchar(255)` | Yes | Optional physical description |
| `loaded_at` | `timestamptz` | Yes | When physically loaded |
| `delivered_at` | `timestamptz` | Yes | When confirmed delivered |
| `created_at` | `timestamptz` | No | Default current timestamp |
| `created_by` | `varchar(100)` | Yes | User or service account |
| `updated_at` | `timestamptz` | No | Default current timestamp |
| `updated_by` | `varchar(100)` | Yes | User or service account |

Primary key:

- `pk_pallets (id)`

Foreign keys:

- `fk_pallets_delivery_slip_id -> delivery_slips(id)`
- `fk_pallets_split_transport_id -> split_transports(id)` optional
- `fk_pallets_current_warehouse_location_id -> warehouse_locations(id)` optional

Recommended indexes:

- unique index on `pallet_identifier`
- index on `delivery_slip_id`
- index on `split_transport_id`
- index on `current_warehouse_location_id`
- index on `status`

Recommended constraints:

- `package_count >= 0` when present
- `gross_weight_kg >= 0` when present
- if `split_transport_id` is set, the related delivery must be marked split in business logic

Recommended check constraints:

- `char_length(trim(pallet_identifier)) > 0`
- `package_count is null or package_count >= 0`
- `gross_weight_kg is null or gross_weight_kg >= 0`

### `warehouse_locations`

Represents warehouse positions where pallets can be stored, staged, or loaded.

| Field | Type | Null | Notes |
|---|---|---:|---|
| `id` | `bigint` | No | Primary key |
| `location_code` | `varchar(50)` | No | Human-readable unique location code |
| `location_name` | `varchar(100)` | Yes | Optional display name |
| `location_type` | `warehouse_location_type` | No | Operational area type |
| `zone_code` | `varchar(50)` | Yes | Optional warehouse zone |
| `aisle` | `varchar(20)` | Yes | Optional |
| `rack` | `varchar(20)` | Yes | Optional |
| `level` | `varchar(20)` | Yes | Optional |
| `position` | `varchar(20)` | Yes | Optional |
| `is_active` | `boolean` | No | Default `true` |
| `notes` | `text` | Yes | Optional |
| `created_at` | `timestamptz` | No | Default current timestamp |
| `updated_at` | `timestamptz` | No | Default current timestamp |

Primary key:

- `pk_warehouse_locations (id)`

Recommended indexes:

- unique index on `location_code`
- index on `location_type`
- index on `is_active`
- index on `zone_code`

Recommended constraints:

- `location_code` must not be blank

Recommended check constraints:

- `char_length(trim(location_code)) > 0`

### `pallet_movements`

Immutable movement history for warehouse traceability.

| Field | Type | Null | Notes |
|---|---|---:|---|
| `id` | `bigint` | No | Primary key |
| `pallet_id` | `bigint` | No | FK to `pallets.id` |
| `from_location_id` | `bigint` | Yes | FK to `warehouse_locations.id` |
| `to_location_id` | `bigint` | Yes | FK to `warehouse_locations.id` |
| `movement_type` | `pallet_movement_type` | No | Operational movement type |
| `movement_timestamp` | `timestamptz` | No | When movement happened |
| `performed_by` | `varchar(100)` | Yes | User or service account |
| `remarks` | `text` | Yes | Optional reason or note |
| `created_at` | `timestamptz` | No | Default current timestamp |

Primary key:

- `pk_pallet_movements (id)`

Foreign keys:

- `fk_pallet_movements_pallet_id -> pallets(id)`
- `fk_pallet_movements_from_location_id -> warehouse_locations(id)` optional
- `fk_pallet_movements_to_location_id -> warehouse_locations(id)` optional

Recommended indexes:

- index on `pallet_id`
- index on `movement_timestamp`
- index on `movement_type`
- composite index on `(pallet_id, movement_timestamp desc)`
- index on `to_location_id`
- index on `from_location_id`

Recommended constraints:

- at least one of `from_location_id` or `to_location_id` must be present
- `from_location_id` and `to_location_id` should not be identical unless movement type is `CORRECTED`

Recommended check constraints:

- `from_location_id is not null or to_location_id is not null`
- `(from_location_id is null or to_location_id is null or from_location_id <> to_location_id or movement_type = 'CORRECTED')`

### `documents`

Metadata for files stored outside the database. Transport controls completeness and required document handling.

| Field | Type | Null | Notes |
|---|---|---:|---|
| `id` | `bigint` | No | Primary key |
| `delivery_slip_id` | `bigint` | No | FK to `delivery_slips.id` |
| `pallet_id` | `bigint` | Yes | Optional FK if document is tied to one pallet |
| `split_transport_id` | `bigint` | Yes | Optional FK if document belongs to a split transport only |
| `document_type` | `document_type` | No | Type of document |
| `document_status` | `document_status` | No | Availability/completeness state |
| `original_filename` | `varchar(255)` | Yes | Uploaded filename |
| `stored_filename` | `varchar(255)` | Yes | Internal storage filename |
| `storage_relative_path` | `varchar(500)` | Yes | Relative file storage path |
| `mime_type` | `varchar(100)` | Yes | Optional |
| `file_size_bytes` | `bigint` | Yes | Optional |
| `checksum_sha256` | `varchar(64)` | Yes | Optional integrity hash |
| `uploaded_at` | `timestamptz` | Yes | File upload timestamp |
| `uploaded_by` | `varchar(100)` | Yes | User or service account |
| `document_date` | `date` | Yes | Business document date |
| `version_number` | `integer` | No | Default `1` |
| `is_latest_version` | `boolean` | No | Default `true` |
| `remarks` | `text` | Yes | Optional |
| `created_at` | `timestamptz` | No | Default current timestamp |
| `updated_at` | `timestamptz` | No | Default current timestamp |

Primary key:

- `pk_documents (id)`

Foreign keys:

- `fk_documents_delivery_slip_id -> delivery_slips(id)`
- `fk_documents_pallet_id -> pallets(id)` optional
- `fk_documents_split_transport_id -> split_transports(id)` optional

Recommended indexes:

- index on `delivery_slip_id`
- index on `pallet_id`
- index on `split_transport_id`
- index on `document_type`
- index on `document_status`
- composite index on `(delivery_slip_id, document_type)`
- composite index on `(delivery_slip_id, document_type, is_latest_version)`

Recommended constraints:

- signed CMR must be stored as `SIGNED_CMR`, not as `CMR`
- file metadata fields may be null only for expected-but-not-yet-uploaded records
- `version_number >= 1`
- `file_size_bytes >= 0` when present

Recommended check constraints:

- `version_number >= 1`
- `file_size_bytes is null or file_size_bytes >= 0`
- `(document_status <> 'AVAILABLE') or storage_relative_path is not null`

Recommended unique constraints:

- unique on `(delivery_slip_id, pallet_id, split_transport_id, document_type, version_number)`

### `document_print_instructions`

Defines how many copies transport requires per document type for a delivery. This is the operational source for print copy requirements.

| Field | Type | Null | Notes |
|---|---|---:|---|
| `id` | `bigint` | No | Primary key |
| `delivery_slip_id` | `bigint` | No | FK to `delivery_slips.id` |
| `split_transport_id` | `bigint` | Yes | Optional FK for split-specific print requirements |
| `document_type` | `document_type` | No | Document type to print |
| `required_copy_count` | `integer` | No | Number of required print copies |
| `printer_role` | `varchar(50)` | Yes | Example: `WAREHOUSE_MAIN`, `LOADING_DOCK`, `OFFICE` |
| `is_mandatory` | `boolean` | No | Default `true` |
| `notes` | `text` | Yes | Operational print instructions |
| `created_at` | `timestamptz` | No | Default current timestamp |
| `created_by` | `varchar(100)` | Yes | User or service account |
| `updated_at` | `timestamptz` | No | Default current timestamp |
| `updated_by` | `varchar(100)` | Yes | User or service account |

Primary key:

- `pk_document_print_instructions (id)`

Foreign keys:

- `fk_document_print_instructions_delivery_slip_id -> delivery_slips(id)`
- `fk_document_print_instructions_split_transport_id -> split_transports(id)` optional

Recommended indexes:

- index on `delivery_slip_id`
- index on `split_transport_id`
- index on `document_type`
- composite index on `(delivery_slip_id, document_type)`

Recommended unique constraints:

- unique on `(delivery_slip_id, split_transport_id, document_type, printer_role)`

Recommended check constraints:

- `required_copy_count >= 0`
- if `required_copy_count = 0`, `is_mandatory` should usually be `false` by application rule

### `print_jobs`

Tracks print execution requests and outcomes for operational auditing.

| Field | Type | Null | Notes |
|---|---|---:|---|
| `id` | `bigint` | No | Primary key |
| `delivery_slip_id` | `bigint` | Yes | FK to `delivery_slips.id` |
| `document_id` | `bigint` | Yes | FK to `documents.id` |
| `split_transport_id` | `bigint` | Yes | Optional FK |
| `target_type` | `print_target_type` | No | What this job printed |
| `printer_name` | `varchar(200)` | No | Resolved destination printer |
| `requested_copy_count` | `integer` | No | Requested copies |
| `printed_copy_count` | `integer` | Yes | Actual result when known |
| `status` | `print_job_status` | No | Print state |
| `queued_at` | `timestamptz` | No | When job entered queue |
| `started_at` | `timestamptz` | Yes | When spool/send started |
| `completed_at` | `timestamptz` | Yes | When result finalized |
| `requested_by` | `varchar(100)` | Yes | User or service account |
| `error_message` | `text` | Yes | Failure details |
| `created_at` | `timestamptz` | No | Default current timestamp |

Primary key:

- `pk_print_jobs (id)`

Foreign keys:

- `fk_print_jobs_delivery_slip_id -> delivery_slips(id)` optional
- `fk_print_jobs_document_id -> documents(id)` optional
- `fk_print_jobs_split_transport_id -> split_transports(id)` optional

Recommended indexes:

- index on `delivery_slip_id`
- index on `document_id`
- index on `split_transport_id`
- index on `status`
- index on `queued_at`
- composite index on `(printer_name, queued_at desc)`

Recommended constraints:

- at least one print target reference should be present
- `requested_copy_count >= 1`
- `printed_copy_count >= 0` when present

Recommended check constraints:

- `delivery_slip_id is not null or document_id is not null or split_transport_id is not null`
- `requested_copy_count >= 1`
- `printed_copy_count is null or printed_copy_count >= 0`

### `audit_logs`

Business and security relevant action log. This is for traceability, not low-level technical diagnostics.

| Field | Type | Null | Notes |
|---|---|---:|---|
| `id` | `bigint` | No | Primary key |
| `occurred_at` | `timestamptz` | No | Event time |
| `entity_type` | `audit_entity_type` | No | Type of entity acted on |
| `entity_id` | `bigint` | Yes | ID of affected record when applicable |
| `action_type` | `audit_action_type` | No | Action performed |
| `delivery_slip_id` | `bigint` | Yes | Optional business context |
| `pallet_id` | `bigint` | Yes | Optional business context |
| `document_id` | `bigint` | Yes | Optional business context |
| `split_transport_id` | `bigint` | Yes | Optional business context |
| `performed_by` | `varchar(100)` | Yes | User or service account |
| `source_system` | `varchar(100)` | Yes | Desktop client, API, import process, etc. |
| `details_json` | `jsonb` | Yes | Structured before/after detail |
| `created_at` | `timestamptz` | No | Default current timestamp |

Primary key:

- `pk_audit_logs (id)`

Foreign keys:

- `fk_audit_logs_delivery_slip_id -> delivery_slips(id)` optional
- `fk_audit_logs_pallet_id -> pallets(id)` optional
- `fk_audit_logs_document_id -> documents(id)` optional
- `fk_audit_logs_split_transport_id -> split_transports(id)` optional

Recommended indexes:

- index on `occurred_at`
- index on `entity_type`
- composite index on `(entity_type, entity_id, occurred_at desc)`
- index on `delivery_slip_id`
- index on `pallet_id`
- index on `document_id`
- index on `performed_by`

Recommended constraints:

- `action_type` must always be present
- `details_json` should stay lightweight and structured

### `application_logs`

Technical application logging table. Use only for important persisted logs; most routine runtime logs can also go to files or centralized logging.

| Field | Type | Null | Notes |
|---|---|---:|---|
| `id` | `bigint` | No | Primary key |
| `logged_at` | `timestamptz` | No | Log event time |
| `log_level` | `application_log_level` | No | Severity |
| `logger_name` | `varchar(200)` | No | Module or logger source |
| `message` | `text` | No | Rendered log message |
| `exception_type` | `varchar(200)` | Yes | Optional exception type |
| `exception_message` | `text` | Yes | Optional exception message |
| `context_json` | `jsonb` | Yes | Structured context |
| `delivery_slip_id` | `bigint` | Yes | Optional business reference |
| `pallet_id` | `bigint` | Yes | Optional business reference |
| `document_id` | `bigint` | Yes | Optional business reference |
| `request_id` | `varchar(100)` | Yes | Correlation ID |
| `created_at` | `timestamptz` | No | Default current timestamp |

Primary key:

- `pk_application_logs (id)`

Foreign keys:

- `fk_application_logs_delivery_slip_id -> delivery_slips(id)` optional
- `fk_application_logs_pallet_id -> pallets(id)` optional
- `fk_application_logs_document_id -> documents(id)` optional

Recommended indexes:

- index on `logged_at`
- index on `log_level`
- index on `logger_name`
- index on `request_id`
- index on `delivery_slip_id`

Recommended constraints:

- `message` must not be blank
- consider time-based retention or partitioning later if table growth becomes large

Recommended check constraints:

- `char_length(trim(message)) > 0`

## Optional Rare Split Transport Structure

This structure should only be used when one delivery must be operationally divided into multiple transport legs or transport handling groups. It is intentionally lightweight.

### `split_transports`

| Field | Type | Null | Notes |
|---|---|---:|---|
| `id` | `bigint` | No | Primary key |
| `delivery_slip_id` | `bigint` | No | FK to `delivery_slips.id` |
| `split_code` | `varchar(50)` | No | Business identifier such as `A`, `B`, or `LEG-1` |
| `transport_reference` | `varchar(100)` | Yes | Optional transport-specific reference |
| `sequence_number` | `integer` | No | Display and ordering |
| `status` | `varchar(50)` or enum | No | Operational split status |
| `notes` | `text` | Yes | Optional |
| `created_at` | `timestamptz` | No | Default current timestamp |
| `created_by` | `varchar(100)` | Yes | User or service account |
| `updated_at` | `timestamptz` | No | Default current timestamp |
| `updated_by` | `varchar(100)` | Yes | User or service account |

Primary key:

- `pk_split_transports (id)`

Foreign keys:

- `fk_split_transports_delivery_slip_id -> delivery_slips(id)`

Recommended indexes:

- index on `delivery_slip_id`
- composite unique index on `(delivery_slip_id, split_code)`
- composite unique index on `(delivery_slip_id, sequence_number)`

Recommended check constraints:

- `sequence_number >= 1`
- `char_length(trim(split_code)) > 0`

### Why This Is Lightweight

- The main workflow still starts from `delivery_slips`.
- Most tables attach directly to `delivery_slips`.
- Only pallets, documents, print instructions, print jobs, and audit records optionally reference `split_transports`.
- No split record is required in the normal case.
- The UI can keep split transport hidden unless `delivery_slips.is_split_transport = true`.

## Relationship Summary

- One `delivery_slips` row has many `pallets`
- One `delivery_slips` row has many `documents`
- One `delivery_slips` row has many `document_print_instructions`
- One `delivery_slips` row has many `print_jobs`
- One `pallets` row has many `pallet_movements`
- One `warehouse_locations` row is referenced by many pallets and movements
- One `delivery_slips` row may have many `split_transports`
- One `split_transports` row may have many pallets, documents, print instructions, print jobs, and audit log entries

## Additional Recommendations

### Foreign key delete behavior

Recommended default approach:

- Avoid hard deletes for business records after operational use.
- Prefer application-level archival or status-based deactivation.
- Use `ON DELETE RESTRICT` or `ON DELETE NO ACTION` for most business references.
- Use `ON DELETE SET NULL` only where nullable contextual references are acceptable.

### Naming conventions

Recommended conventions for migrations and ORM mapping:

- primary keys: `pk_<table_name>`
- foreign keys: `fk_<table_name>_<column_name>`
- unique constraints: `uq_<table_name>_<column_list>`
- indexes: `ix_<table_name>_<column_list>`
- check constraints: `ck_<table_name>_<rule_name>`

### Timestamps

Recommended on most mutable tables:

- `created_at not null default now()`
- `updated_at not null default now()`

For strict consistency, manage `updated_at` in the application or through a simple trigger if company standards allow it.

### File storage

Do not store file binaries in PostgreSQL.

Store only:

- file path
- original filename
- stored filename
- size
- mime type
- checksum
- upload metadata

### Logging split

Keep two different persisted logging concerns:

- `audit_logs` for business traceability and accountability
- `application_logs` for technical diagnostics and support

This separation makes internal support and compliance reviews much easier later.

## Suggested Next Step

The next implementation step should be to translate this schema into:

1. SQLAlchemy ORM models
2. Alembic initial migration
3. enum definitions shared consistently between ORM and service layer
