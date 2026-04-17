"""Extend print jobs for copy tracking and reprints.

Revision ID: 20260416_0003
Revises: 20260416_0002
Create Date: 2026-04-16 01:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260416_0003"
down_revision = "20260416_0002"
branch_labels = None
depends_on = None


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


def upgrade() -> None:
    op.add_column(
        "print_jobs",
        sa.Column("document_type", document_type, nullable=True),
    )
    op.add_column("print_jobs", sa.Column("printer_role", sa.String(length=50), nullable=True))
    op.add_column(
        "print_jobs",
        sa.Column(
            "is_manual_printer_override",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("print_jobs", sa.Column("reprint_of_print_job_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_print_jobs_reprint_of_print_job_id"),
        "print_jobs",
        "print_jobs",
        ["reprint_of_print_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_print_jobs_reprint_of_print_job_id"),
        "print_jobs",
        ["reprint_of_print_job_id"],
        unique=False,
    )
    op.create_index(op.f("ix_print_jobs_document_type"), "print_jobs", ["document_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_print_jobs_document_type"), table_name="print_jobs")
    op.drop_index(op.f("ix_print_jobs_reprint_of_print_job_id"), table_name="print_jobs")
    op.drop_constraint(
        op.f("fk_print_jobs_reprint_of_print_job_id"),
        "print_jobs",
        type_="foreignkey",
    )
    op.drop_column("print_jobs", "reprint_of_print_job_id")
    op.drop_column("print_jobs", "is_manual_printer_override")
    op.drop_column("print_jobs", "printer_role")
    op.drop_column("print_jobs", "document_type")
