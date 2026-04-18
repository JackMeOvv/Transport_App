from datetime import UTC, datetime
from logistics_app.desktop.workflow.workflow_store import DesktopWorkflowStore, DeliveryWorkflowRecord
from logistics_app.data.models.enums import DeliverySlipStatus

def test_set_loading_info():
    store = DesktopWorkflowStore()
    delivery = store.current_delivery()
    slip_number = delivery.delivery_slip_number

    store.set_loading_info(
        delivery_slip_number=slip_number,
        expected_loading_date="2026-05-20",
        carrier_name="Test Carrier",
        changed_by="test_user"
    )

    updated_delivery = store.get_delivery(slip_number)
    assert updated_delivery.expected_loading_date == "2026-05-20"
    assert updated_delivery.carrier_name == "Test Carrier"

    # Check audit log
    events = store.audit_events_for_delivery(slip_number)
    assert any("Loading info set: Date=2026-05-20, Carrier=Test Carrier." in e.details for e in events)

def test_initial_deliveries_have_carrier():
    store = DesktopWorkflowStore()
    delivery = store.get_delivery("DEL-2026-0142")
    assert delivery.carrier_name == "QuickLogistics North"
