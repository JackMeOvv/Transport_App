"""Unit tests for the new workflow store requirements and RBAC."""

from __future__ import annotations

import pytest
from logistics_app.desktop.workflow.workflow_store import DesktopWorkflowStore
from logistics_app.data.models.enums import DeliverySlipStatus, DocumentType

def test_default_requirements_are_zero():
    store = DesktopWorkflowStore()
    delivery = store.current_delivery()
    for requirement in delivery.print_requirements.values():
        assert requirement.required_copies == 0

def test_release_validation_at_least_one_requirement():
    store = DesktopWorkflowStore()
    # Create a fresh delivery with no documents
    delivery = store.create_delivery("Test Customer", "Test Dest", 1, "test.user", "DEL-TEST-001")

    # Initially no requirements
    with pytest.raises(ValueError, match="At least one required document must be set before release"):
        store.release_delivery(delivery.delivery_slip_number, "test.user")

def test_release_validation_missing_documents():
    store = DesktopWorkflowStore()
    # Create a fresh delivery with no documents (except Sticker which is auto-generated)
    delivery = store.create_delivery("Test Customer", "Test Dest", 1, "test.user", "DEL-TEST-002")

    # Set a requirement for Packing Slip
    store.set_required_copies(delivery.delivery_slip_number, DocumentType.PACKING_SLIP, 1, "test.user")

    # No Packing Slip uploaded yet
    with pytest.raises(ValueError, match="Missing required documents: Packing Slip"):
        store.release_delivery(delivery.delivery_slip_number, "test.user")

def test_release_validation_success():
    store = DesktopWorkflowStore()
    delivery = store.create_delivery("Test Customer", "Test Dest", 1, "test.user", "DEL-TEST-003")

    # Set a requirement
    store.set_required_copies(delivery.delivery_slip_number, DocumentType.PACKING_SLIP, 1, "test.user")
    # Upload the document
    store.upload_document(delivery.delivery_slip_number, DocumentType.PACKING_SLIP, "test.pdf", "test.user")

    # Should succeed now
    store.release_delivery(delivery.delivery_slip_number, "test.user")
    assert delivery.status == DeliverySlipStatus.RELEASED_BY_TRANSPORT

def test_rbac_roles():
    store = DesktopWorkflowStore()
    assert store.user_role() == "admin"

    store.set_user_role("warehouse")
    assert store.user_role() == "warehouse"

    with pytest.raises(ValueError, match="Invalid role"):
        store.set_user_role("invalid_role")

def test_delete_delivery():
    store = DesktopWorkflowStore()
    delivery = store.current_delivery()
    slip_number = delivery.delivery_slip_number

    store.delete_delivery(slip_number, "admin.user")

    with pytest.raises(KeyError):
        store.get_delivery(slip_number)
