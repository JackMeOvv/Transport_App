"""Shared desktop workflow state for the operational demo client."""

from logistics_app.desktop.workflow.workflow_store import (
    AuditEventRecord,
    DeliveryWorkflowRecord,
    DesktopWorkflowStore,
    DocumentWorkflowRecord,
    PalletWorkflowRecord,
    PrintRequirementRecord,
    get_workflow_store,
)

__all__ = [
    "AuditEventRecord",
    "DeliveryWorkflowRecord",
    "DesktopWorkflowStore",
    "DocumentWorkflowRecord",
    "PalletWorkflowRecord",
    "PrintRequirementRecord",
    "get_workflow_store",
]
