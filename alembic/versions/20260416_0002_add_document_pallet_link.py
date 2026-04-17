"""Add optional pallet link to documents.

Revision ID: 20260416_0002
Revises: 20260416_0001
Create Date: 2026-04-16 00:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260416_0002"
down_revision = "20260416_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("pallet_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_documents_pallet_id"),
        "documents",
        "pallets",
        ["pallet_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_documents_pallet_id"), "documents", ["pallet_id"], unique=False)

    op.drop_constraint(
        op.f("uq_documents_delivery_slip_id_split_transport_id_document_type_version_number"),
        "documents",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_documents_delivery_slip_id_pallet_id_split_transport_id_document_type_version_number"),
        "documents",
        ["delivery_slip_id", "pallet_id", "split_transport_id", "document_type", "version_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("uq_documents_delivery_slip_id_pallet_id_split_transport_id_document_type_version_number"),
        "documents",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_documents_delivery_slip_id_split_transport_id_document_type_version_number"),
        "documents",
        ["delivery_slip_id", "split_transport_id", "document_type", "version_number"],
    )
    op.drop_index(op.f("ix_documents_pallet_id"), table_name="documents")
    op.drop_constraint(op.f("fk_documents_pallet_id"), "documents", type_="foreignkey")
    op.drop_column("documents", "pallet_id")
