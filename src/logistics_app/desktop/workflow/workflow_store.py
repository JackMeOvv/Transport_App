"""Shared in-process workflow state for the desktop client.

This module intentionally keeps the workflow explicit and readable.
It lets the existing desktop screens behave like one application while the
backend integration is still being completed.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import count
from pathlib import Path
import tempfile

from PySide6.QtCore import QObject, Signal

from logistics_app.data.models.enums import DeliverySlipStatus, DocumentType, PalletStatus


def _humanize_document_type(document_type: DocumentType) -> str:
    return document_type.value.replace("_", " ").title()


def _humanize_delivery_status(status: DeliverySlipStatus) -> str:
    return status.value.replace("_", " ").title()


def _document_filename_prefix(document_type: DocumentType) -> str:
    return {
        DocumentType.PACKING_SLIP: "PackingSlip",
        DocumentType.CMR: "CMR",
        DocumentType.SIGNED_CMR: "SignedCMR",
        DocumentType.CERTIFICATE: "Certificate",
        DocumentType.STICKER: "Sticker",
        DocumentType.TRANSPORT_DOCUMENT: "TransportDocument",
        DocumentType.OTHER: "Document",
    }[document_type]


@dataclass(slots=True)
class DocumentWorkflowRecord:
    """Document metadata used by the desktop workflow."""

    document_type: DocumentType
    filename: str
    stored_filename: str
    version: int
    uploaded_by: str
    uploaded_at: datetime
    source_path: str | None = None
    is_available: bool = True

    @property
    def title(self) -> str:
        return _humanize_document_type(self.document_type)

    @property
    def metadata_text(self) -> str:
        return (
            f"Version {self.version} | Uploaded by {self.uploaded_by} | "
            f"{self.uploaded_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M UTC')}"
        )


@dataclass(slots=True)
class PrintRequirementRecord:
    """Transport-defined print requirement and warehouse execution state."""

    document_type: DocumentType
    required_copies: int
    printed_copies: int
    default_printer: str
    printer_override: str | None = None
    document_instances: int = 0

    @property
    def remaining_copies(self) -> int:
        return max(self.effective_required_copies - self.printed_copies, 0)

    @property
    def effective_required_copies(self) -> int:
        return self.required_copies * self.document_instances

    @property
    def active_printer(self) -> str:
        return self.printer_override or self.default_printer


@dataclass(slots=True)
class PalletWorkflowRecord:
    """Pallet state tracked on warehouse screens."""

    pallet_id: str
    status: PalletStatus
    current_location: str
    packages: int
    last_movement: str
    ready_to_load: bool = False


@dataclass(slots=True)
class AuditEventRecord:
    """Simple readable desktop audit event."""

    occurred_at: datetime
    event_name: str
    delivery_slip_number: str
    performed_by: str
    details: str


@dataclass(slots=True)
class DeliveryWorkflowRecord:
    """Shared delivery workflow state used by the desktop client."""

    delivery_slip_number: str
    customer_name: str
    destination_name: str
    transport_reference: str
    delivery_date: str
    origin_name: str
    status: DeliverySlipStatus
    expected_loading_date: str | None
    pallets: list[PalletWorkflowRecord]
    print_requirements: dict[DocumentType, PrintRequirementRecord]
    documents: dict[DocumentType, DocumentWorkflowRecord]
    transport_notes: str
    correction_notes: list[str]
    carrier_name: str | None = None
    document_history: dict[DocumentType, list[DocumentWorkflowRecord]] = field(default_factory=dict)
    claimed_by: str | None = None
    claimed_at: str | None = None
    signed_cmr_expected: bool = True
    signed_cmr_uploaded: bool = False
    shipped_at: str | None = None
    split_exception: bool = False

    @property
    def required_document_types(self) -> set[DocumentType]:
        return {
            document_type
            for document_type, requirement in self.print_requirements.items()
            if requirement.required_copies > 0
            and document_type not in {DocumentType.SIGNED_CMR}
        }

    @property
    def loaded_pallets(self) -> int:
        return sum(1 for pallet in self.pallets if pallet.status == PalletStatus.LOADED)

    @property
    def total_pallets(self) -> int:
        return len(self.pallets)

    @property
    def loading_progress_percent(self) -> int:
        if self.total_pallets == 0:
            return 0
        return int((self.loaded_pallets / self.total_pallets) * 100)

    @property
    def missing_pallets(self) -> list[PalletWorkflowRecord]:
        return [pallet for pallet in self.pallets if pallet.status != PalletStatus.LOADED]

    @property
    def is_loading_complete(self) -> bool:
        return self.total_pallets > 0 and self.loaded_pallets == self.total_pallets

    @property
    def available_document_types(self) -> set[DocumentType]:
        return set(self.documents.keys())

    def documents_for_type(self, document_type: DocumentType) -> list[DocumentWorkflowRecord]:
        history = self.document_history.get(document_type)
        if history is not None:
            return list(history)
        latest = self.documents.get(document_type)
        return [latest] if latest is not None else []

    def uploaded_document_count(self, document_type: DocumentType) -> int:
        return len(self.documents_for_type(document_type))

    @property
    def is_ready_for_release(self) -> bool:
        return self.required_document_types.issubset(self.available_document_types)

    @property
    def signed_cmr_status_text(self) -> str:
        if not self.signed_cmr_expected:
            return "Not Applicable"
        if self.signed_cmr_uploaded:
            return "Uploaded"
        if self.status in {DeliverySlipStatus.SHIPPED, DeliverySlipStatus.COMPLETED}:
            return "Pending"
        return "Expected Later"

    @property
    def transport_readiness_text(self) -> str:
        if self.status in {
            DeliverySlipStatus.RELEASED_BY_TRANSPORT,
            DeliverySlipStatus.READY_TO_LOAD,
            DeliverySlipStatus.LOADING_IN_PROGRESS,
            DeliverySlipStatus.SHIPPED,
            DeliverySlipStatus.COMPLETED,
        }:
            return "Ready"
        if self.is_ready_for_release:
            return "Pending Release"
        return "Pending Documents"


class DesktopWorkflowStore(QObject):
    """Small shared desktop workflow store for the current process."""

    workflow_changed = Signal()
    current_delivery_changed = Signal(object)
    navigation_requested = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self._sequence = count(147)
        self._current_delivery_slip_number: str | None = "DEL-2026-0142"
        self._audit_events: list[AuditEventRecord] = []
        self._transport_operator_name = ""
        self._deliveries = self._build_initial_deliveries()

    def current_delivery(self) -> DeliveryWorkflowRecord | None:
        if self._current_delivery_slip_number is None:
            return None
        return self.get_delivery(self._current_delivery_slip_number)

    def get_delivery(self, delivery_slip_number: str) -> DeliveryWorkflowRecord:
        return self._deliveries[delivery_slip_number]

    def all_deliveries(self) -> list[DeliveryWorkflowRecord]:
        return list(self._deliveries.values())

    def active_deliveries(self) -> list[DeliveryWorkflowRecord]:
        active_statuses = {
            DeliverySlipStatus.CREATED,
            DeliverySlipStatus.STORED,
            DeliverySlipStatus.DOCUMENTS_IN_PREPARATION,
            DeliverySlipStatus.RELEASED_BY_TRANSPORT,
            DeliverySlipStatus.READY_TO_LOAD,
            DeliverySlipStatus.LOADING_IN_PROGRESS,
        }
        return [
            delivery
            for delivery in self.all_deliveries()
            if delivery.status in active_statuses
        ]

    def transport_new_deliveries(self) -> list[DeliveryWorkflowRecord]:
        """Deliveries that still need transport preparation or release."""
        new_statuses = {
            DeliverySlipStatus.CREATED,
            DeliverySlipStatus.STORED,
            DeliverySlipStatus.DOCUMENTS_IN_PREPARATION,
        }
        return [
            delivery
            for delivery in self.all_deliveries()
            if delivery.status in new_statuses
        ]

    def released_deliveries(self) -> list[DeliveryWorkflowRecord]:
        """Deliveries already released by transport and visible to warehouse."""
        released_statuses = {
            DeliverySlipStatus.RELEASED_BY_TRANSPORT,
            DeliverySlipStatus.READY_TO_LOAD,
            DeliverySlipStatus.LOADING_IN_PROGRESS,
        }
        return [
            delivery
            for delivery in self.all_deliveries()
            if delivery.status in released_statuses
        ]

    def sent_deliveries(self) -> list[DeliveryWorkflowRecord]:
        sent_statuses = {DeliverySlipStatus.SHIPPED, DeliverySlipStatus.COMPLETED}
        return [
            delivery
            for delivery in self.all_deliveries()
            if delivery.status in sent_statuses
        ]

    def set_current_delivery(self, delivery_slip_number: str | None) -> None:
        if delivery_slip_number is not None and delivery_slip_number not in self._deliveries:
            raise ValueError(f"Unknown delivery slip: {delivery_slip_number}")
        self._current_delivery_slip_number = delivery_slip_number
        self.current_delivery_changed.emit(delivery_slip_number)
        self.workflow_changed.emit()

    def find_delivery_by_reference(self, reference_text: str) -> DeliveryWorkflowRecord:
        reference = reference_text.strip().upper()
        if not reference:
            current = self.current_delivery()
            if current is None:
                raise ValueError("No delivery is currently selected. Please enter a reference.")
            return current
        if reference in self._deliveries:
            return self._deliveries[reference]

        for delivery in self._deliveries.values():
            for pallet in delivery.pallets:
                if pallet.pallet_id.upper() == reference:
                    return delivery
        raise ValueError(f"No delivery found for reference '{reference_text}'.")

    def create_delivery(
        self,
        customer_name: str,
        destination_name: str,
        pallet_count: int,
        created_by: str,
        delivery_slip_number: str | None = None,
    ) -> DeliveryWorkflowRecord:
        if delivery_slip_number is not None:
            delivery_number = delivery_slip_number.strip().upper()
            if not delivery_number:
                raise ValueError("Delivery slip number cannot be empty.")
            if delivery_number in self._deliveries:
                raise ValueError(f"Delivery slip {delivery_number} already exists.")
        else:
            delivery_number = f"DEL-2026-{next(self._sequence):04d}"
        pallets = [
            PalletWorkflowRecord(
                pallet_id=f"PAL-{delivery_number.split('-')[-1]}-{index:03d}",
                status=PalletStatus.REGISTERED,
                current_location="Receiving",
                packages=6 + (index % 4),
                last_movement="Created",
                ready_to_load=False,
            )
            for index in range(1, pallet_count + 1)
        ]
        delivery = DeliveryWorkflowRecord(
            delivery_slip_number=delivery_number,
            customer_name=customer_name,
            destination_name=destination_name,
            transport_reference=f"TRP-{next(self._sequence):05d}",
            delivery_date="2026-04-17",
            origin_name="Moerdijk Warehouse",
            status=DeliverySlipStatus.STORED,
            expected_loading_date=None,
            pallets=pallets,
            print_requirements=self._default_print_requirements(),
            documents={},
            transport_notes="New delivery created by warehouse. Awaiting transport document preparation.",
            correction_notes=[],
        )
        self._regenerate_sticker_document(delivery, uploaded_by="warehouse.system")
        self._deliveries[delivery_number] = delivery
        self._log_event(
            event_name="delivery_slip_created",
            delivery_slip_number=delivery_number,
            performed_by=created_by,
            details=f"Delivery created for {customer_name} with {pallet_count} pallets.",
        )
        self.set_current_delivery(delivery_number)
        return delivery

    def adjust_pallet_count(
        self,
        delivery_slip_number: str,
        new_pallet_count: int,
        changed_by: str,
    ) -> None:
        """Adjust pallet count after corrections and regenerate pallet stickers."""
        if new_pallet_count <= 0:
            raise ValueError("Pallet count must be greater than zero.")

        delivery = self.get_delivery(delivery_slip_number)
        old_count = len(delivery.pallets)
        if new_pallet_count == old_count:
            return

        if new_pallet_count > old_count:
            for index in range(old_count + 1, new_pallet_count + 1):
                delivery.pallets.append(
                    PalletWorkflowRecord(
                        pallet_id=f"PAL-{delivery.delivery_slip_number.split('-')[-1]}-{index:03d}",
                        status=PalletStatus.REGISTERED,
                        current_location="Receiving",
                        packages=1,
                        last_movement="Correction added",
                        ready_to_load=False,
                    )
                )
        else:
            delivery.pallets = delivery.pallets[:new_pallet_count]

        correction_note = (
            f"{datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} | "
            f"{changed_by} changed pallet count from {old_count} to {new_pallet_count}."
        )
        delivery.correction_notes.append(correction_note)
        delivery.transport_notes = (
            f"{delivery.transport_notes}\nCorrection: pallet count changed from "
            f"{old_count} to {new_pallet_count} by {changed_by}."
        ).strip()
        self._regenerate_sticker_document(delivery, uploaded_by=changed_by)
        self._log_event(
            event_name="delivery_slip_changed",
            delivery_slip_number=delivery_slip_number,
            performed_by=changed_by,
            details=f"Pallet count corrected from {old_count} to {new_pallet_count}.",
        )
        self.workflow_changed.emit()

    def set_loading_info(
        self,
        delivery_slip_number: str,
        expected_loading_date: str,
        carrier_name: str,
        changed_by: str,
    ) -> None:
        """Store the transport-provided expected loading date and carrier name."""
        delivery = self.get_delivery(delivery_slip_number)
        delivery.expected_loading_date = expected_loading_date.strip()
        delivery.carrier_name = carrier_name.strip()
        self._log_event(
            event_name="delivery_slip_changed",
            delivery_slip_number=delivery_slip_number,
            performed_by=changed_by,
            details=(
                f"Loading info set: Date={delivery.expected_loading_date}, "
                f"Carrier={delivery.carrier_name}."
            ),
        )
        self.workflow_changed.emit()

    def request_navigation(self, target_workspace: str, delivery_slip_number: str) -> None:
        """Ask the desktop shell to switch to a workspace for the selected delivery."""
        self.set_current_delivery(delivery_slip_number)
        self.navigation_requested.emit(target_workspace, delivery_slip_number)

    def transport_operator_name(self) -> str:
        return self._transport_operator_name

    def set_transport_operator_name(self, operator_name: str) -> None:
        self._transport_operator_name = operator_name.strip()
        self.workflow_changed.emit()

    def claim_delivery(self, delivery_slip_number: str, claimed_by: str) -> None:
        delivery = self.get_delivery(delivery_slip_number)
        operator_name = claimed_by.strip()
        if not operator_name:
            raise ValueError("Enter your colleague name in Transport settings first.")
        if delivery.claimed_by and delivery.claimed_by != operator_name:
            raise ValueError(f"{delivery.delivery_slip_number} is already claimed by {delivery.claimed_by}.")
        delivery.claimed_by = operator_name
        delivery.claimed_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        self._log_event(
            event_name="delivery_slip_changed",
            delivery_slip_number=delivery_slip_number,
            performed_by=operator_name,
            details=f"Shipment claimed by {operator_name}.",
        )
        self.workflow_changed.emit()

    def release_delivery_claim(self, delivery_slip_number: str, released_by: str) -> None:
        delivery = self.get_delivery(delivery_slip_number)
        operator_name = released_by.strip()
        if not delivery.claimed_by:
            return
        if operator_name and delivery.claimed_by != operator_name:
            raise ValueError(f"{delivery.delivery_slip_number} is currently claimed by {delivery.claimed_by}.")
        previous_owner = delivery.claimed_by
        delivery.claimed_by = None
        delivery.claimed_at = None
        self._log_event(
            event_name="delivery_slip_changed",
            delivery_slip_number=delivery_slip_number,
            performed_by=operator_name or previous_owner or "transport.office",
            details=f"Shipment claim released (previous owner: {previous_owner}).",
        )
        self.workflow_changed.emit()

    def upload_document(
        self,
        delivery_slip_number: str,
        document_type: DocumentType,
        filename: str,
        uploaded_by: str,
        source_path: str | None = None,
    ) -> DocumentWorkflowRecord:
        delivery = self.get_delivery(delivery_slip_number)
        document_history = delivery.document_history.setdefault(document_type, [])
        version = len(document_history) + 1
        stored_filename = f"{delivery.delivery_slip_number}_{document_type.value}_{version:02d}.bin"
        record = DocumentWorkflowRecord(
            document_type=document_type,
            filename=filename,
            stored_filename=stored_filename,
            version=version,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.now(UTC),
            source_path=source_path,
        )
        document_history.append(record)
        delivery.documents[document_type] = record
        self._sync_print_document_instances(delivery, document_type)
        if document_type == DocumentType.SIGNED_CMR:
            delivery.signed_cmr_uploaded = True
            if delivery.status == DeliverySlipStatus.SHIPPED:
                delivery.status = DeliverySlipStatus.COMPLETED
        elif delivery.status == DeliverySlipStatus.CREATED:
            delivery.status = DeliverySlipStatus.DOCUMENTS_IN_PREPARATION

        event_name = (
            "signed_cmr_uploaded"
            if document_type == DocumentType.SIGNED_CMR
            else "document_uploaded"
        )
        if delivery.status in {DeliverySlipStatus.SHIPPED, DeliverySlipStatus.COMPLETED} and document_type != DocumentType.SIGNED_CMR:
            event_name = "document_added_after_shipment"

        self._log_event(
            event_name=event_name,
            delivery_slip_number=delivery_slip_number,
            performed_by=uploaded_by,
            details=f"{_humanize_document_type(document_type)} uploaded as {filename}.",
        )
        self.workflow_changed.emit()
        return record

    def set_required_copies(
        self,
        delivery_slip_number: str,
        document_type: DocumentType,
        required_copies: int,
        changed_by: str,
    ) -> None:
        delivery = self.get_delivery(delivery_slip_number)
        requirement = delivery.print_requirements[document_type]
        requirement.required_copies = max(required_copies, 0)
        self._log_event(
            event_name="print_instruction_changed",
            delivery_slip_number=delivery_slip_number,
            performed_by=changed_by,
            details=(
                f"{_humanize_document_type(document_type)} now requires "
                f"{requirement.required_copies} copies."
            ),
        )
        self.workflow_changed.emit()

    def set_printer_override(
        self,
        delivery_slip_number: str,
        document_type: DocumentType,
        printer_name: str,
        changed_by: str,
    ) -> None:
        delivery = self.get_delivery(delivery_slip_number)
        requirement = delivery.print_requirements[document_type]
        requirement.printer_override = printer_name.strip()
        self._log_event(
            event_name="print_instruction_changed",
            delivery_slip_number=delivery_slip_number,
            performed_by=changed_by,
            details=(
                f"{_humanize_document_type(document_type)} printer override set to "
                f"{requirement.printer_override}."
            ),
        )
        self.workflow_changed.emit()

    def print_document(
        self,
        delivery_slip_number: str,
        document_type: DocumentType,
        copies: int,
        requested_by: str,
        is_reprint: bool = False,
    ) -> None:
        delivery = self.get_delivery(delivery_slip_number)
        requirement = delivery.print_requirements[document_type]
        if requirement.effective_required_copies <= 0 and not is_reprint:
            raise ValueError(
                f"No printable copies are configured for {_humanize_document_type(document_type)}."
            )
        requirement.printed_copies += max(copies, 0)
        details = (
            f"{copies} copies of {_humanize_document_type(document_type)} sent to "
            f"{requirement.active_printer}."
        )
        if is_reprint:
            details += " Reprint requested."
        self._log_event(
            event_name="print_action_requested",
            delivery_slip_number=delivery_slip_number,
            performed_by=requested_by,
            details=details,
        )
        self.workflow_changed.emit()

    def release_delivery(self, delivery_slip_number: str, released_by: str) -> None:
        delivery = self.get_delivery(delivery_slip_number)
        delivery.status = DeliverySlipStatus.RELEASED_BY_TRANSPORT
        self._log_event(
            event_name="transport_document_readiness_confirmed",
            delivery_slip_number=delivery_slip_number,
            performed_by=released_by,
            details=(
                "Transport released the shipment to warehouse based on the transport checklist "
                "and operational decision."
            ),
        )
        self.workflow_changed.emit()

    def assign_pallet_location(
        self,
        delivery_slip_number: str,
        pallet_id: str,
        location_code: str,
        moved_by: str,
    ) -> None:
        pallet = self._get_pallet(delivery_slip_number, pallet_id)
        previous_location = pallet.current_location
        pallet.current_location = location_code
        pallet.status = PalletStatus.IN_WAREHOUSE
        pallet.ready_to_load = False
        pallet.last_movement = f"Assigned to {location_code}"
        delivery = self.get_delivery(delivery_slip_number)
        if delivery.status == DeliverySlipStatus.CREATED:
            delivery.status = DeliverySlipStatus.STORED
        self._log_event(
            event_name="pallet_assigned",
            delivery_slip_number=delivery_slip_number,
            performed_by=moved_by,
            details=f"{pallet_id} assigned to {location_code} from {previous_location}.",
        )
        self.workflow_changed.emit()

    def move_pallet(
        self,
        delivery_slip_number: str,
        pallet_id: str,
        location_code: str,
        reason: str,
        moved_by: str,
    ) -> None:
        pallet = self._get_pallet(delivery_slip_number, pallet_id)
        previous_location = pallet.current_location
        pallet.current_location = location_code
        pallet.ready_to_load = "dock" in location_code.lower() or "truck" in location_code.lower()
        pallet.status = PalletStatus.STAGED if pallet.ready_to_load else PalletStatus.IN_WAREHOUSE
        pallet.last_movement = reason
        self._log_event(
            event_name="pallet_moved",
            delivery_slip_number=delivery_slip_number,
            performed_by=moved_by,
            details=f"{pallet_id} moved from {previous_location} to {location_code} ({reason}).",
        )
        self.workflow_changed.emit()

    def mark_pallet_loaded(
        self,
        delivery_slip_number: str,
        pallet_id: str,
        loaded_by: str,
    ) -> None:
        delivery = self.get_delivery(delivery_slip_number)
        pallet = self._get_pallet(delivery_slip_number, pallet_id)
        pallet.current_location = "Loaded to truck"
        pallet.status = PalletStatus.LOADED
        pallet.ready_to_load = True
        pallet.last_movement = "Loaded"
        if delivery.status in {
            DeliverySlipStatus.RELEASED_BY_TRANSPORT,
            DeliverySlipStatus.READY_TO_LOAD,
        }:
            delivery.status = DeliverySlipStatus.LOADING_IN_PROGRESS
        self._log_event(
            event_name="pallet_marked_loaded",
            delivery_slip_number=delivery_slip_number,
            performed_by=loaded_by,
            details=f"{pallet_id} marked as loaded.",
        )
        self.workflow_changed.emit()

    def loading_summary(self, delivery_slip_number: str) -> dict[str, object]:
        delivery = self.get_delivery(delivery_slip_number)
        return {
            "expected_pallets": delivery.total_pallets,
            "loaded_pallets": delivery.loaded_pallets,
            "missing_pallets": [pallet.pallet_id for pallet in delivery.missing_pallets],
            "is_complete": delivery.is_loading_complete,
        }

    def finalize_shipment(
        self,
        delivery_slip_number: str,
        finalized_by: str,
    ) -> dict[str, object]:
        delivery = self.get_delivery(delivery_slip_number)
        summary = self.loading_summary(delivery_slip_number)
        if not summary["is_complete"]:
            return summary

        delivery.status = DeliverySlipStatus.SHIPPED
        delivery.shipped_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        self._log_event(
            event_name="loading_completed",
            delivery_slip_number=delivery_slip_number,
            performed_by=finalized_by,
            details=(
                f"All {delivery.total_pallets} pallets loaded. Shipment marked as shipped."
            ),
        )
        self._log_event(
            event_name="status_changed_to_shipped",
            delivery_slip_number=delivery_slip_number,
            performed_by=finalized_by,
            details="Delivery moved from active queue to sent history.",
        )
        self.workflow_changed.emit()
        return summary

    def audit_events_for_delivery(self, delivery_slip_number: str) -> list[AuditEventRecord]:
        return [
            event
            for event in self._audit_events
            if event.delivery_slip_number == delivery_slip_number
        ]

    def _get_pallet(self, delivery_slip_number: str, pallet_id: str) -> PalletWorkflowRecord:
        delivery = self.get_delivery(delivery_slip_number)
        for pallet in delivery.pallets:
            if pallet.pallet_id.upper() == pallet_id.strip().upper():
                return pallet
        raise ValueError(f"Pallet '{pallet_id}' is not linked to {delivery_slip_number}.")

    def _log_event(
        self,
        event_name: str,
        delivery_slip_number: str,
        performed_by: str,
        details: str,
    ) -> None:
        self._audit_events.append(
            AuditEventRecord(
                occurred_at=datetime.now(UTC),
                event_name=event_name,
                delivery_slip_number=delivery_slip_number,
                performed_by=performed_by,
                details=details,
            )
        )

    def _sync_print_document_instances(
        self,
        delivery: DeliveryWorkflowRecord,
        document_type: DocumentType,
    ) -> None:
        requirement = delivery.print_requirements.get(document_type)
        if requirement is None:
            return
        if document_type == DocumentType.STICKER:
            requirement.document_instances = 1 if document_type in delivery.documents else 0
            return
        requirement.document_instances = delivery.uploaded_document_count(document_type)

    def _default_print_requirements(self) -> dict[DocumentType, PrintRequirementRecord]:
        return {
            DocumentType.PACKING_SLIP: PrintRequirementRecord(
                document_type=DocumentType.PACKING_SLIP,
                required_copies=2,
                printed_copies=0,
                default_printer="Warehouse_Main_01",
            ),
            DocumentType.CMR: PrintRequirementRecord(
                document_type=DocumentType.CMR,
                required_copies=2,
                printed_copies=0,
                default_printer="Warehouse_Main_01",
            ),
            DocumentType.CERTIFICATE: PrintRequirementRecord(
                document_type=DocumentType.CERTIFICATE,
                required_copies=1,
                printed_copies=0,
                default_printer="Office_01",
            ),
            DocumentType.STICKER: PrintRequirementRecord(
                document_type=DocumentType.STICKER,
                required_copies=1,
                printed_copies=0,
                default_printer="Label_01",
            ),
            DocumentType.TRANSPORT_DOCUMENT: PrintRequirementRecord(
                document_type=DocumentType.TRANSPORT_DOCUMENT,
                required_copies=1,
                printed_copies=0,
                default_printer="Warehouse_Main_01",
            ),
            DocumentType.SIGNED_CMR: PrintRequirementRecord(
                document_type=DocumentType.SIGNED_CMR,
                required_copies=0,
                printed_copies=0,
                default_printer="Office_01",
            ),
        }

    def _build_initial_deliveries(self) -> dict[str, DeliveryWorkflowRecord]:
        deliveries: list[DeliveryWorkflowRecord] = []

        delivery_0142 = DeliveryWorkflowRecord(
            delivery_slip_number="DEL-2026-0142",
            customer_name="Nordic Export BV",
            destination_name="Rotterdam Terminal",
            transport_reference="TRP-54821",
            delivery_date="2026-04-17",
            origin_name="Moerdijk Warehouse",
            status=DeliverySlipStatus.RELEASED_BY_TRANSPORT,
            expected_loading_date="2026-04-18",
            carrier_name="QuickLogistics North",
            pallets=[
                PalletWorkflowRecord("PAL-0142-001", PalletStatus.IN_WAREHOUSE, "A-01-03", 8, "Put away"),
                PalletWorkflowRecord("PAL-0142-002", PalletStatus.IN_WAREHOUSE, "A-01-04", 10, "Put away"),
                PalletWorkflowRecord("PAL-0142-003", PalletStatus.STAGED, "Dock 2", 6, "Stage for loading", True),
                PalletWorkflowRecord("PAL-0142-004", PalletStatus.STAGED, "Dock 2", 4, "Stage for loading", True),
                PalletWorkflowRecord("PAL-0142-005", PalletStatus.STAGED, "Dock 2", 7, "Stage for loading", True),
            ],
            print_requirements=self._default_print_requirements(),
            documents={},
            transport_notes=(
                "Customer requires certificate print with outbound pack. "
                "Signed CMR will be uploaded after loading."
            ),
            correction_notes=[],
        )
        for document_type in [
            DocumentType.PACKING_SLIP,
            DocumentType.CMR,
            DocumentType.CERTIFICATE,
            DocumentType.STICKER,
            DocumentType.TRANSPORT_DOCUMENT,
        ]:
            delivery_0142.documents[document_type] = DocumentWorkflowRecord(
                document_type=document_type,
                filename=f"{_document_filename_prefix(document_type)}_{delivery_0142.delivery_slip_number}.pdf",
                stored_filename=f"{delivery_0142.delivery_slip_number}_{document_type.value}_01.bin",
                version=1,
                uploaded_by="transport.office",
                uploaded_at=datetime.now(UTC),
            )
        deliveries.append(delivery_0142)

        delivery_0145 = DeliveryWorkflowRecord(
            delivery_slip_number="DEL-2026-0145",
            customer_name="Harbor Export Group",
            destination_name="Lille",
            transport_reference="TRP-54822",
            delivery_date="2026-04-17",
            origin_name="Moerdijk Warehouse",
            status=DeliverySlipStatus.DOCUMENTS_IN_PREPARATION,
            expected_loading_date=None,
            pallets=[
                PalletWorkflowRecord("PAL-0145-001", PalletStatus.IN_WAREHOUSE, "B-02-01", 5, "Received"),
                PalletWorkflowRecord("PAL-0145-002", PalletStatus.IN_WAREHOUSE, "B-02-02", 5, "Received"),
                PalletWorkflowRecord("PAL-0145-003", PalletStatus.IN_WAREHOUSE, "B-02-03", 4, "Received"),
            ],
            print_requirements=self._default_print_requirements(),
            documents={
                DocumentType.PACKING_SLIP: DocumentWorkflowRecord(
                    document_type=DocumentType.PACKING_SLIP,
                    filename="PackingSlip_DEL-2026-0145.pdf",
                    stored_filename="DEL-2026-0145_PACKING_SLIP_01.bin",
                    version=1,
                    uploaded_by="transport.office",
                    uploaded_at=datetime.now(UTC),
                ),
            },
            transport_notes="Certificate and CMR still pending from transport.",
            correction_notes=[],
        )
        deliveries.append(delivery_0145)

        delivery_0140 = DeliveryWorkflowRecord(
            delivery_slip_number="DEL-2026-0140",
            customer_name="Global Trade Co",
            destination_name="Hamburg",
            transport_reference="TRP-54819",
            delivery_date="2026-04-12",
            origin_name="Moerdijk Warehouse",
            status=DeliverySlipStatus.COMPLETED,
            expected_loading_date="2026-04-12",
            carrier_name="Euro Freight BV",
            pallets=[
                PalletWorkflowRecord("PAL-0140-001", PalletStatus.LOADED, "Loaded to truck", 6, "Loaded", True),
                PalletWorkflowRecord("PAL-0140-002", PalletStatus.LOADED, "Loaded to truck", 6, "Loaded", True),
            ],
            print_requirements=self._default_print_requirements(),
            documents={},
            transport_notes="Completed shipment with signed CMR on file.",
            correction_notes=[],
            signed_cmr_uploaded=True,
            shipped_at="2026-04-12 14:05 UTC",
        )
        for document_type in [
            DocumentType.PACKING_SLIP,
            DocumentType.CMR,
            DocumentType.CERTIFICATE,
            DocumentType.SIGNED_CMR,
        ]:
            delivery_0140.documents[document_type] = DocumentWorkflowRecord(
                document_type=document_type,
                filename=f"{_document_filename_prefix(document_type)}_{delivery_0140.delivery_slip_number}.pdf",
                stored_filename=f"{delivery_0140.delivery_slip_number}_{document_type.value}_01.bin",
                version=1,
                uploaded_by="transport.office",
                uploaded_at=datetime.now(UTC),
            )
        deliveries.append(delivery_0140)

        delivery_0141 = DeliveryWorkflowRecord(
            delivery_slip_number="DEL-2026-0141",
            customer_name="Euro Parts Ltd",
            destination_name="Antwerp",
            transport_reference="TRP-54820",
            delivery_date="2026-04-13",
            origin_name="Moerdijk Warehouse",
            status=DeliverySlipStatus.SHIPPED,
            expected_loading_date="2026-04-13",
            carrier_name="Harbor Linkage",
            pallets=[
                PalletWorkflowRecord("PAL-0141-001", PalletStatus.LOADED, "Loaded to truck", 6, "Loaded", True),
                PalletWorkflowRecord("PAL-0141-002", PalletStatus.LOADED, "Loaded to truck", 6, "Loaded", True),
                PalletWorkflowRecord("PAL-0141-003", PalletStatus.LOADED, "Loaded to truck", 6, "Loaded", True),
            ],
            print_requirements=self._default_print_requirements(),
            documents={
                DocumentType.PACKING_SLIP: DocumentWorkflowRecord(
                    document_type=DocumentType.PACKING_SLIP,
                    filename="PackingSlip_DEL-2026-0141.pdf",
                    stored_filename="DEL-2026-0141_PACKING_SLIP_01.bin",
                    version=1,
                    uploaded_by="transport.office",
                    uploaded_at=datetime.now(UTC),
                ),
                DocumentType.CMR: DocumentWorkflowRecord(
                    document_type=DocumentType.CMR,
                    filename="CMR_DEL-2026-0141.pdf",
                    stored_filename="DEL-2026-0141_CMR_01.bin",
                    version=1,
                    uploaded_by="transport.office",
                    uploaded_at=datetime.now(UTC),
                ),
            },
            transport_notes="Signed CMR still pending from carrier return.",
            correction_notes=[],
            shipped_at="2026-04-13 11:45 UTC",
        )
        deliveries.append(delivery_0141)

        initialized_deliveries = {delivery.delivery_slip_number: deepcopy(delivery) for delivery in deliveries}
        for delivery in initialized_deliveries.values():
            self._initialize_document_tracking(delivery)
        return initialized_deliveries

    def _initialize_document_tracking(self, delivery: DeliveryWorkflowRecord) -> None:
        """Backfill per-type document history and print totals for seeded deliveries."""
        for document_type, record in delivery.documents.items():
            delivery.document_history[document_type] = [record]
        for document_type in delivery.print_requirements:
            self._sync_print_document_instances(delivery, document_type)

    def _regenerate_sticker_document(
        self,
        delivery: DeliveryWorkflowRecord,
        uploaded_by: str,
    ) -> None:
        """Generate pallet sticker labels with Code 128 barcodes for each pallet."""
        sticker_history = delivery.document_history.setdefault(DocumentType.STICKER, [])
        version = len(sticker_history) + 1
        filename = f"PalletStickers_{delivery.delivery_slip_number}.zpl"
        stored_filename = f"{delivery.delivery_slip_number}_{DocumentType.STICKER.value}_{version:02d}.zpl"
        source_path = self._write_sticker_file(delivery, filename)

        sticker_record = DocumentWorkflowRecord(
            document_type=DocumentType.STICKER,
            filename=filename,
            stored_filename=stored_filename,
            version=version,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.now(UTC),
            source_path=source_path,
        )
        sticker_history.append(sticker_record)
        delivery.documents[DocumentType.STICKER] = sticker_record
        self._sync_print_document_instances(delivery, DocumentType.STICKER)

    def _write_sticker_file(self, delivery: DeliveryWorkflowRecord, filename: str) -> str:
        """Create a ZPL label file with Code 128 barcodes for the delivery pallets."""
        output_dir = Path(tempfile.gettempdir()) / "internal-logistics-stickers"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        output_path.write_text(self._build_sticker_zpl(delivery), encoding="utf-8")
        return str(output_path)

    def _build_sticker_zpl(self, delivery: DeliveryWorkflowRecord) -> str:
        """Build ZPL content with a scannable Code 128 barcode per pallet."""
        labels: list[str] = []
        for index, pallet in enumerate(delivery.pallets, start=1):
            labels.append(
                "\n".join(
                    [
                        "^XA",
                        "^PW800",
                        "^LL600",
                        "^FO40,40^A0N,36,36^FDInternal Logistics^FS",
                        f"^FO40,90^A0N,34,34^FDDelivery: {delivery.delivery_slip_number}^FS",
                        f"^FO40,140^A0N,34,34^FDPallet {index} of {len(delivery.pallets)}^FS",
                        f"^FO40,190^A0N,42,42^FD{pallet.pallet_id}^FS",
                        "^BY3,2,140",
                        f"^FO40,260^BCN,140,Y,N,N^FD{pallet.pallet_id}^FS",
                        "^XZ",
                    ]
                )
            )
        return "\n".join(labels) + "\n"


_workflow_store: DesktopWorkflowStore | None = None


def get_workflow_store() -> DesktopWorkflowStore:
    """Return the shared desktop workflow store."""
    global _workflow_store
    if _workflow_store is None:
        _workflow_store = DesktopWorkflowStore()
    return _workflow_store
