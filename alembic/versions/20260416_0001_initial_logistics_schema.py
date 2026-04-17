"""Initial logistics schema.

Revision ID: 20260416_0001
Revises:
Create Date: 2026-04-16 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260416_0001"
down_revision = None
branch_labels = None
depends_on = None


delivery_slip_status = sa.Enum(
    "REGISTERED",
    "IN_WAREHOUSE",
    "READY_TO_LOAD",
    "LOADED",
    "DISPATCHED",
    "DELIVERED",
    "CANCELLED",
    name="delivery_slip_status",
    native_enum=False,
    create_constraint=True,
)

split_transport_status = sa.Enum(
    "PLANNED",
    "READY_TO_LOAD",
    "LOADED",
    "DISPATCHED",
    "COMPLETED",
    "CANCELLED",
    name="split_transport_status",
    native_enum=False,
    create_constraint=True,
)

document_type = sa.Enum(
    "PACKING_SLIP",
    "CMR",
    "SIGNED_CMR",
    "CERTIFICATE",
    "STICKER",
    "TRANSPORT_DOCUMENT",
    "OTHER",
    name="document_type",
    native_enum=False,
    create_constraint=True,
)

document_status = sa.Enum(
    "EXPECTED",
    "AVAILABLE",
    "MISSING",
    "SUPERSEDED",
    "ARCHIVED",
    name="document_status",
    native_enum=False,
    create_constraint=True,
)

pallet_status = sa.Enum(
    "REGISTERED",
    "IN_WAREHOUSE",
    "STAGED",
    "LOADED",
    "DISPATCHED",
    "DELIVERED",
    "LOST",
    "DAMAGED",
    name="pallet_status",
    native_enum=False,
    create_constraint=True,
)

warehouse_location_type = sa.Enum(
    "RECEIVING",
    "STORAGE",
    "STAGING",
    "LOADING_DOCK",
    "QUARANTINE",
    "OUTBOUND_BUFFER",
    name="warehouse_location_type",
    native_enum=False,
    create_constraint=True,
)

pallet_movement_type = sa.Enum(
    "RECEIVED",
    "PUT_AWAY",
    "RELOCATED",
    "STAGED_FOR_LOADING",
    "LOADED",
    "UNLOADED",
    "CORRECTED",
    name="pallet_movement_type",
    native_enum=False,
    create_constraint=True,
)

print_target_type = sa.Enum(
    "DELIVERY",
    "DOCUMENT",
    "SPLIT_TRANSPORT",
    name="print_target_type",
    native_enum=False,
    create_constraint=True,
)

print_job_status = sa.Enum(
    "QUEUED",
    "SENT",
    "PRINTED",
    "FAILED",
    "CANCELLED",
    name="print_job_status",
    native_enum=False,
    create_constraint=True,
)

audit_entity_type = sa.Enum(
    "DELIVERY_SLIP",
    "PALLET",
    "WAREHOUSE_LOCATION",
    "DOCUMENT",
    "PRINT_JOB",
    "SPLIT_TRANSPORT",
    "SYSTEM",
    name="audit_entity_type",
    native_enum=False,
    create_constraint=True,
)

audit_action_type = sa.Enum(
    "CREATE",
    "UPDATE",
    "DELETE",
    "STATUS_CHANGE",
    "PRINT",
    "UPLOAD",
    "MOVE",
    "LOAD",
    "UNLOAD",
    "LOGIN",
    "LOGOUT",
    name="audit_action_type",
    native_enum=False,
    create_constraint=True,
)

application_log_level = sa.Enum(
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
    name="application_log_level",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "delivery_slips",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("delivery_slip_number", sa.String(length=50), nullable=False),
        sa.Column("customer_reference", sa.String(length=100), nullable=True),
        sa.Column("customer_name", sa.String(length=200), nullable=True),
        sa.Column("delivery_date", sa.Date(), nullable=True),
        sa.Column("origin_name", sa.String(length=200), nullable=True),
        sa.Column("destination_name", sa.String(length=200), nullable=True),
        sa.Column("transport_reference", sa.String(length=100), nullable=True),
        sa.Column("status", delivery_slip_status, nullable=False),
        sa.Column("is_split_transport", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.CheckConstraint(
            "char_length(trim(delivery_slip_number)) > 0",
            name=op.f("ck_delivery_slips_delivery_slip_number_not_blank"),
        ),
    )
    op.create_index(op.f("ix_delivery_slips_delivery_date"), "delivery_slips", ["delivery_date"], unique=False)
    op.create_index(op.f("ix_delivery_slips_delivery_slip_number"), "delivery_slips", ["delivery_slip_number"], unique=True)
    op.create_index(op.f("ix_delivery_slips_is_split_transport"), "delivery_slips", ["is_split_transport"], unique=False)
    op.create_index(op.f("ix_delivery_slips_status"), "delivery_slips", ["status"], unique=False)
    op.create_index(op.f("ix_delivery_slips_transport_reference"), "delivery_slips", ["transport_reference"], unique=False)

    op.create_table(
        "warehouse_locations",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("location_code", sa.String(length=50), nullable=False),
        sa.Column("location_name", sa.String(length=100), nullable=True),
        sa.Column("location_type", warehouse_location_type, nullable=False),
        sa.Column("zone_code", sa.String(length=50), nullable=True),
        sa.Column("aisle", sa.String(length=20), nullable=True),
        sa.Column("rack", sa.String(length=20), nullable=True),
        sa.Column("level", sa.String(length=20), nullable=True),
        sa.Column("position", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "char_length(trim(location_code)) > 0",
            name=op.f("ck_warehouse_locations_location_code_not_blank"),
        ),
    )
    op.create_index(op.f("ix_warehouse_locations_is_active"), "warehouse_locations", ["is_active"], unique=False)
    op.create_index(op.f("ix_warehouse_locations_location_code"), "warehouse_locations", ["location_code"], unique=True)
    op.create_index(op.f("ix_warehouse_locations_location_type"), "warehouse_locations", ["location_type"], unique=False)
    op.create_index(op.f("ix_warehouse_locations_zone_code"), "warehouse_locations", ["zone_code"], unique=False)

    op.create_table(
        "split_transports",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("delivery_slip_id", sa.BigInteger(), nullable=False),
        sa.Column("split_code", sa.String(length=50), nullable=False),
        sa.Column("transport_reference", sa.String(length=100), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("status", split_transport_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.CheckConstraint("sequence_number >= 1", name=op.f("ck_split_transports_sequence_number_positive")),
        sa.CheckConstraint("char_length(trim(split_code)) > 0", name=op.f("ck_split_transports_split_code_not_blank")),
        sa.ForeignKeyConstraint(["delivery_slip_id"], ["delivery_slips.id"], name=op.f("fk_split_transports_delivery_slip_id"), ondelete="RESTRICT"),
        sa.UniqueConstraint("delivery_slip_id", "sequence_number", name=op.f("uq_split_transports_delivery_slip_id_sequence_number")),
        sa.UniqueConstraint("delivery_slip_id", "split_code", name=op.f("uq_split_transports_delivery_slip_id_split_code")),
    )
    op.create_index(op.f("ix_split_transports_delivery_slip_id"), "split_transports", ["delivery_slip_id"], unique=False)

    op.create_table(
        "pallets",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("delivery_slip_id", sa.BigInteger(), nullable=False),
        sa.Column("pallet_identifier", sa.String(length=100), nullable=False),
        sa.Column("split_transport_id", sa.BigInteger(), nullable=True),
        sa.Column("current_warehouse_location_id", sa.BigInteger(), nullable=True),
        sa.Column("status", pallet_status, nullable=False),
        sa.Column("gross_weight_kg", sa.Numeric(12, 3), nullable=True),
        sa.Column("package_count", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.CheckConstraint("char_length(trim(pallet_identifier)) > 0", name=op.f("ck_pallets_pallet_identifier_not_blank")),
        sa.CheckConstraint("package_count is null or package_count >= 0", name=op.f("ck_pallets_package_count_not_negative")),
        sa.CheckConstraint("gross_weight_kg is null or gross_weight_kg >= 0", name=op.f("ck_pallets_gross_weight_not_negative")),
        sa.ForeignKeyConstraint(["current_warehouse_location_id"], ["warehouse_locations.id"], name=op.f("fk_pallets_current_warehouse_location_id"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["delivery_slip_id"], ["delivery_slips.id"], name=op.f("fk_pallets_delivery_slip_id"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["split_transport_id"], ["split_transports.id"], name=op.f("fk_pallets_split_transport_id"), ondelete="RESTRICT"),
    )
    op.create_index(op.f("ix_pallets_current_warehouse_location_id"), "pallets", ["current_warehouse_location_id"], unique=False)
    op.create_index(op.f("ix_pallets_delivery_slip_id"), "pallets", ["delivery_slip_id"], unique=False)
    op.create_index(op.f("ix_pallets_pallet_identifier"), "pallets", ["pallet_identifier"], unique=True)
    op.create_index(op.f("ix_pallets_split_transport_id"), "pallets", ["split_transport_id"], unique=False)
    op.create_index(op.f("ix_pallets_status"), "pallets", ["status"], unique=False)

    op.create_table(
        "documents",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("delivery_slip_id", sa.BigInteger(), nullable=False),
        sa.Column("split_transport_id", sa.BigInteger(), nullable=True),
        sa.Column("document_type", document_type, nullable=False),
        sa.Column("document_status", document_status, nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("stored_filename", sa.String(length=255), nullable=True),
        sa.Column("storage_relative_path", sa.String(length=500), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_by", sa.String(length=100), nullable=True),
        sa.Column("document_date", sa.Date(), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_latest_version", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("version_number >= 1", name=op.f("ck_documents_version_number_positive")),
        sa.CheckConstraint("file_size_bytes is null or file_size_bytes >= 0", name=op.f("ck_documents_file_size_not_negative")),
        sa.CheckConstraint(
            "document_status <> 'AVAILABLE' or storage_relative_path is not null",
            name=op.f("ck_documents_available_document_has_storage_path"),
        ),
        sa.ForeignKeyConstraint(["delivery_slip_id"], ["delivery_slips.id"], name=op.f("fk_documents_delivery_slip_id"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["split_transport_id"], ["split_transports.id"], name=op.f("fk_documents_split_transport_id"), ondelete="RESTRICT"),
        sa.UniqueConstraint("delivery_slip_id", "split_transport_id", "document_type", "version_number", name=op.f("uq_documents_delivery_slip_id_split_transport_id_document_type_version_number")),
    )
    op.create_index(op.f("ix_documents_delivery_slip_id"), "documents", ["delivery_slip_id"], unique=False)
    op.create_index(op.f("ix_documents_document_status"), "documents", ["document_status"], unique=False)
    op.create_index(op.f("ix_documents_document_type"), "documents", ["document_type"], unique=False)
    op.create_index("ix_documents_delivery_slip_id_document_type", "documents", ["delivery_slip_id", "document_type"], unique=False)
    op.create_index("ix_documents_delivery_slip_id_document_type_is_latest_version", "documents", ["delivery_slip_id", "document_type", "is_latest_version"], unique=False)
    op.create_index(op.f("ix_documents_split_transport_id"), "documents", ["split_transport_id"], unique=False)

    op.create_table(
        "document_print_instructions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("delivery_slip_id", sa.BigInteger(), nullable=False),
        sa.Column("split_transport_id", sa.BigInteger(), nullable=True),
        sa.Column("document_type", document_type, nullable=False),
        sa.Column("required_copy_count", sa.Integer(), nullable=False),
        sa.Column("printer_role", sa.String(length=50), nullable=True),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.CheckConstraint("required_copy_count >= 0", name=op.f("ck_document_print_instructions_required_copy_count_not_negative")),
        sa.ForeignKeyConstraint(["delivery_slip_id"], ["delivery_slips.id"], name=op.f("fk_document_print_instructions_delivery_slip_id"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["split_transport_id"], ["split_transports.id"], name=op.f("fk_document_print_instructions_split_transport_id"), ondelete="RESTRICT"),
        sa.UniqueConstraint("delivery_slip_id", "split_transport_id", "document_type", "printer_role", name=op.f("uq_document_print_instructions_delivery_slip_id_split_transport_id_document_type_printer_role")),
    )
    op.create_index(op.f("ix_document_print_instructions_delivery_slip_id"), "document_print_instructions", ["delivery_slip_id"], unique=False)
    op.create_index("ix_document_print_instructions_delivery_slip_id_document_type", "document_print_instructions", ["delivery_slip_id", "document_type"], unique=False)
    op.create_index(op.f("ix_document_print_instructions_document_type"), "document_print_instructions", ["document_type"], unique=False)
    op.create_index(op.f("ix_document_print_instructions_split_transport_id"), "document_print_instructions", ["split_transport_id"], unique=False)

    op.create_table(
        "pallet_movements",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("pallet_id", sa.BigInteger(), nullable=False),
        sa.Column("from_location_id", sa.BigInteger(), nullable=True),
        sa.Column("to_location_id", sa.BigInteger(), nullable=True),
        sa.Column("movement_type", pallet_movement_type, nullable=False),
        sa.Column("movement_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("performed_by", sa.String(length=100), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("from_location_id is not null or to_location_id is not null", name=op.f("ck_pallet_movements_movement_has_location")),
        sa.CheckConstraint(
            """
            from_location_id is null
            or to_location_id is null
            or from_location_id <> to_location_id
            or movement_type = 'CORRECTED'
            """,
            name=op.f("ck_pallet_movements_movement_location_change_or_corrected"),
        ),
        sa.ForeignKeyConstraint(["from_location_id"], ["warehouse_locations.id"], name=op.f("fk_pallet_movements_from_location_id"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pallet_id"], ["pallets.id"], name=op.f("fk_pallet_movements_pallet_id"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["to_location_id"], ["warehouse_locations.id"], name=op.f("fk_pallet_movements_to_location_id"), ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_pallet_movements_from_location_id"), "pallet_movements", ["from_location_id"], unique=False)
    op.create_index(op.f("ix_pallet_movements_movement_timestamp"), "pallet_movements", ["movement_timestamp"], unique=False)
    op.create_index(op.f("ix_pallet_movements_movement_type"), "pallet_movements", ["movement_type"], unique=False)
    op.create_index(op.f("ix_pallet_movements_pallet_id"), "pallet_movements", ["pallet_id"], unique=False)
    op.create_index("ix_pallet_movements_pallet_id_movement_timestamp", "pallet_movements", ["pallet_id", "movement_timestamp"], unique=False)
    op.create_index(op.f("ix_pallet_movements_to_location_id"), "pallet_movements", ["to_location_id"], unique=False)

    op.create_table(
        "print_jobs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("delivery_slip_id", sa.BigInteger(), nullable=True),
        sa.Column("document_id", sa.BigInteger(), nullable=True),
        sa.Column("split_transport_id", sa.BigInteger(), nullable=True),
        sa.Column("target_type", print_target_type, nullable=False),
        sa.Column("printer_name", sa.String(length=200), nullable=False),
        sa.Column("requested_copy_count", sa.Integer(), nullable=False),
        sa.Column("printed_copy_count", sa.Integer(), nullable=True),
        sa.Column("status", print_job_status, nullable=False),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("delivery_slip_id is not null or document_id is not null or split_transport_id is not null", name=op.f("ck_print_jobs_print_job_has_target_reference")),
        sa.CheckConstraint("requested_copy_count >= 1", name=op.f("ck_print_jobs_requested_copy_count_positive")),
        sa.CheckConstraint("printed_copy_count is null or printed_copy_count >= 0", name=op.f("ck_print_jobs_printed_copy_count_not_negative")),
        sa.ForeignKeyConstraint(["delivery_slip_id"], ["delivery_slips.id"], name=op.f("fk_print_jobs_delivery_slip_id"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name=op.f("fk_print_jobs_document_id"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["split_transport_id"], ["split_transports.id"], name=op.f("fk_print_jobs_split_transport_id"), ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_print_jobs_delivery_slip_id"), "print_jobs", ["delivery_slip_id"], unique=False)
    op.create_index(op.f("ix_print_jobs_document_id"), "print_jobs", ["document_id"], unique=False)
    op.create_index(op.f("ix_print_jobs_queued_at"), "print_jobs", ["queued_at"], unique=False)
    op.create_index("ix_print_jobs_printer_name_queued_at", "print_jobs", ["printer_name", "queued_at"], unique=False)
    op.create_index(op.f("ix_print_jobs_split_transport_id"), "print_jobs", ["split_transport_id"], unique=False)
    op.create_index(op.f("ix_print_jobs_status"), "print_jobs", ["status"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entity_type", audit_entity_type, nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=True),
        sa.Column("action_type", audit_action_type, nullable=False),
        sa.Column("delivery_slip_id", sa.BigInteger(), nullable=True),
        sa.Column("pallet_id", sa.BigInteger(), nullable=True),
        sa.Column("document_id", sa.BigInteger(), nullable=True),
        sa.Column("split_transport_id", sa.BigInteger(), nullable=True),
        sa.Column("performed_by", sa.String(length=100), nullable=True),
        sa.Column("source_system", sa.String(length=100), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["delivery_slip_id"], ["delivery_slips.id"], name=op.f("fk_audit_logs_delivery_slip_id"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name=op.f("fk_audit_logs_document_id"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pallet_id"], ["pallets.id"], name=op.f("fk_audit_logs_pallet_id"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["split_transport_id"], ["split_transports.id"], name=op.f("fk_audit_logs_split_transport_id"), ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_audit_logs_delivery_slip_id"), "audit_logs", ["delivery_slip_id"], unique=False)
    op.create_index("ix_audit_logs_entity_type_entity_id_occurred_at", "audit_logs", ["entity_type", "entity_id", "occurred_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_entity_type"), "audit_logs", ["entity_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_document_id"), "audit_logs", ["document_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_occurred_at"), "audit_logs", ["occurred_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_pallet_id"), "audit_logs", ["pallet_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_performed_by"), "audit_logs", ["performed_by"], unique=False)
    op.create_index(op.f("ix_audit_logs_split_transport_id"), "audit_logs", ["split_transport_id"], unique=False)

    op.create_table(
        "application_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("log_level", application_log_level, nullable=False),
        sa.Column("logger_name", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("exception_type", sa.String(length=200), nullable=True),
        sa.Column("exception_message", sa.Text(), nullable=True),
        sa.Column("context_json", sa.JSON(), nullable=True),
        sa.Column("delivery_slip_id", sa.BigInteger(), nullable=True),
        sa.Column("pallet_id", sa.BigInteger(), nullable=True),
        sa.Column("document_id", sa.BigInteger(), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("char_length(trim(message)) > 0", name=op.f("ck_application_logs_message_not_blank")),
        sa.ForeignKeyConstraint(["delivery_slip_id"], ["delivery_slips.id"], name=op.f("fk_application_logs_delivery_slip_id"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name=op.f("fk_application_logs_document_id"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pallet_id"], ["pallets.id"], name=op.f("fk_application_logs_pallet_id"), ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_application_logs_delivery_slip_id"), "application_logs", ["delivery_slip_id"], unique=False)
    op.create_index(op.f("ix_application_logs_document_id"), "application_logs", ["document_id"], unique=False)
    op.create_index(op.f("ix_application_logs_log_level"), "application_logs", ["log_level"], unique=False)
    op.create_index(op.f("ix_application_logs_logged_at"), "application_logs", ["logged_at"], unique=False)
    op.create_index(op.f("ix_application_logs_logger_name"), "application_logs", ["logger_name"], unique=False)
    op.create_index(op.f("ix_application_logs_pallet_id"), "application_logs", ["pallet_id"], unique=False)
    op.create_index(op.f("ix_application_logs_request_id"), "application_logs", ["request_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_application_logs_request_id"), table_name="application_logs")
    op.drop_index(op.f("ix_application_logs_pallet_id"), table_name="application_logs")
    op.drop_index(op.f("ix_application_logs_logger_name"), table_name="application_logs")
    op.drop_index(op.f("ix_application_logs_logged_at"), table_name="application_logs")
    op.drop_index(op.f("ix_application_logs_log_level"), table_name="application_logs")
    op.drop_index(op.f("ix_application_logs_document_id"), table_name="application_logs")
    op.drop_index(op.f("ix_application_logs_delivery_slip_id"), table_name="application_logs")
    op.drop_table("application_logs")

    op.drop_index(op.f("ix_audit_logs_split_transport_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_performed_by"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_pallet_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_occurred_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_document_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_entity_type"), table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_type_entity_id_occurred_at", table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_delivery_slip_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_print_jobs_status"), table_name="print_jobs")
    op.drop_index(op.f("ix_print_jobs_split_transport_id"), table_name="print_jobs")
    op.drop_index("ix_print_jobs_printer_name_queued_at", table_name="print_jobs")
    op.drop_index(op.f("ix_print_jobs_queued_at"), table_name="print_jobs")
    op.drop_index(op.f("ix_print_jobs_document_id"), table_name="print_jobs")
    op.drop_index(op.f("ix_print_jobs_delivery_slip_id"), table_name="print_jobs")
    op.drop_table("print_jobs")

    op.drop_index(op.f("ix_pallet_movements_to_location_id"), table_name="pallet_movements")
    op.drop_index("ix_pallet_movements_pallet_id_movement_timestamp", table_name="pallet_movements")
    op.drop_index(op.f("ix_pallet_movements_pallet_id"), table_name="pallet_movements")
    op.drop_index(op.f("ix_pallet_movements_movement_type"), table_name="pallet_movements")
    op.drop_index(op.f("ix_pallet_movements_movement_timestamp"), table_name="pallet_movements")
    op.drop_index(op.f("ix_pallet_movements_from_location_id"), table_name="pallet_movements")
    op.drop_table("pallet_movements")

    op.drop_index(op.f("ix_document_print_instructions_split_transport_id"), table_name="document_print_instructions")
    op.drop_index(op.f("ix_document_print_instructions_document_type"), table_name="document_print_instructions")
    op.drop_index("ix_document_print_instructions_delivery_slip_id_document_type", table_name="document_print_instructions")
    op.drop_index(op.f("ix_document_print_instructions_delivery_slip_id"), table_name="document_print_instructions")
    op.drop_table("document_print_instructions")

    op.drop_index(op.f("ix_documents_split_transport_id"), table_name="documents")
    op.drop_index("ix_documents_delivery_slip_id_document_type_is_latest_version", table_name="documents")
    op.drop_index("ix_documents_delivery_slip_id_document_type", table_name="documents")
    op.drop_index(op.f("ix_documents_document_type"), table_name="documents")
    op.drop_index(op.f("ix_documents_document_status"), table_name="documents")
    op.drop_index(op.f("ix_documents_delivery_slip_id"), table_name="documents")
    op.drop_table("documents")

    op.drop_index(op.f("ix_pallets_status"), table_name="pallets")
    op.drop_index(op.f("ix_pallets_split_transport_id"), table_name="pallets")
    op.drop_index(op.f("ix_pallets_pallet_identifier"), table_name="pallets")
    op.drop_index(op.f("ix_pallets_delivery_slip_id"), table_name="pallets")
    op.drop_index(op.f("ix_pallets_current_warehouse_location_id"), table_name="pallets")
    op.drop_table("pallets")

    op.drop_index(op.f("ix_split_transports_delivery_slip_id"), table_name="split_transports")
    op.drop_table("split_transports")

    op.drop_index(op.f("ix_warehouse_locations_zone_code"), table_name="warehouse_locations")
    op.drop_index(op.f("ix_warehouse_locations_location_type"), table_name="warehouse_locations")
    op.drop_index(op.f("ix_warehouse_locations_location_code"), table_name="warehouse_locations")
    op.drop_index(op.f("ix_warehouse_locations_is_active"), table_name="warehouse_locations")
    op.drop_table("warehouse_locations")

    op.drop_index(op.f("ix_delivery_slips_transport_reference"), table_name="delivery_slips")
    op.drop_index(op.f("ix_delivery_slips_status"), table_name="delivery_slips")
    op.drop_index(op.f("ix_delivery_slips_is_split_transport"), table_name="delivery_slips")
    op.drop_index(op.f("ix_delivery_slips_delivery_slip_number"), table_name="delivery_slips")
    op.drop_index(op.f("ix_delivery_slips_delivery_date"), table_name="delivery_slips")
    op.drop_table("delivery_slips")
