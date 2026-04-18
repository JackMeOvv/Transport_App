"""Warehouse screen for the desktop client."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QInputDialog,
    QPushButton,
    QScrollArea,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from logistics_app.data.models.enums import DeliverySlipStatus, DocumentType
from logistics_app.desktop.ui.dialogs import BaseDialog
from logistics_app.desktop.ui.widgets import ActionToolbar, DataTable, DocumentCard, PageHeader, StatusBadge, SummaryCard
from logistics_app.desktop.workflow import get_workflow_store


@dataclass(slots=True)
class WarehouseDocumentCardData:
    title: str
    filename: str
    metadata: str
    status_text: str
    status_tone: str


@dataclass(slots=True)
class WarehousePrintRow:
    document_type: str
    required_copies: int
    printed_copies: int
    remaining_copies: int
    printer_name: str
    action_state: str


class CreateDeliveryDialog(BaseDialog):
    """Small explicit dialog for warehouse delivery creation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Create Delivery Note", "Create a new delivery note for the warehouse workflow.", parent)
        self.delivery_slip_input = QLineEdit()
        self.customer_input = QLineEdit()
        self.destination_input = QLineEdit()
        self.pallet_count_input = QLineEdit()

        form_layout = QFormLayout()
        form_layout.addRow("Delivery Slip", self.delivery_slip_input)
        form_layout.addRow("Customer", self.customer_input)
        form_layout.addRow("Destination", self.destination_input)
        form_layout.addRow("Pallet Count", self.pallet_count_input)
        self.content_layout.addLayout(form_layout)

        self.create_button = self.add_action_button("Create", role="primary")
        self.cancel_button = self.add_action_button("Cancel")
        self.create_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)


class WarehouseScreenWindow(QMainWindow):
    """Warehouse workspace optimized for pallet handling and fast execution."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Warehouse Workspace")
        self.resize(1520, 980)

        self._workflow_store = get_workflow_store()
        self._workflow_store.workflow_changed.connect(self._refresh_all)
        self._workflow_store.current_delivery_changed.connect(lambda _value: self._refresh_all())
        self._document_cards_by_title: dict[str, DocumentCard] = {}
        self._last_printed_document_type: DocumentType | None = None
        self._displayed_delivery_slip_number: str | None = None

        page_root = QWidget()
        page_root.setObjectName("PageRoot")
        content_layout = QVBoxLayout(page_root)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(18)

        self.page_header = PageHeader(
            title="Warehouse",
            subtitle="Fast workstation flow for pallet handling, loading, and print execution.",
        )
        self._build_header_actions(self.page_header)
        content_layout.addWidget(self.page_header)

        content_layout.addWidget(self._build_scan_panel())
        content_layout.addWidget(self._build_action_toolbar())
        self.summary_cards_layout = self._build_summary_cards()
        content_layout.addLayout(self.summary_cards_layout)

        main_grid = QGridLayout()
        main_grid.setHorizontalSpacing(18)
        main_grid.setVerticalSpacing(18)
        main_grid.addWidget(self._build_transport_readiness_panel(), 0, 0)
        main_grid.addWidget(self._build_signed_cmr_panel(), 0, 1)
        main_grid.addWidget(self._build_pallets_panel(), 1, 0)
        main_grid.addWidget(self._build_location_actions_panel(), 1, 1)
        main_grid.addWidget(self._build_documents_panel(), 2, 0)
        main_grid.addWidget(self._build_print_execution_panel(), 2, 1)
        main_grid.setColumnStretch(0, 3)
        main_grid.setColumnStretch(1, 2)
        content_layout.addLayout(main_grid)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(page_root)
        self.setCentralWidget(scroll_area)
        self._refresh_all()

    def _build_header_actions(self, page_header: PageHeader) -> None:
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_all)
        page_header.add_action_widget(refresh_button)

        create_button = QPushButton("Create Delivery Note")
        create_button.setProperty("buttonRole", "primary")
        create_button.clicked.connect(self._create_delivery)
        page_header.add_action_widget(create_button)

        open_queue_button = QPushButton("Open Load Queue")
        open_queue_button.clicked.connect(self._refresh_all)
        page_header.add_action_widget(open_queue_button)

    def _build_scan_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
        layout = QGridLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)

        title_label = QLabel("Scan or Search")
        title_label.setObjectName("SectionTitle")
        layout.addWidget(title_label, 0, 0, 1, 6)

        helper_label = QLabel("Use pallet ID for the fastest operational flow, or open the main delivery slip when handling a full load.")
        helper_label.setObjectName("PageSubtitle")
        helper_label.setWordWrap(True)
        layout.addWidget(helper_label, 1, 0, 1, 6)

        layout.addWidget(self._caption("Scan Input"), 2, 0)
        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText("Scan pallet ID or enter main delivery slip number")
        self.scan_input.setMinimumHeight(52)
        self.scan_input.setStyleSheet("font-size: 16pt; font-weight: 600;")
        layout.addWidget(self.scan_input, 2, 1, 1, 3)

        open_button = QPushButton("Open")
        open_button.setProperty("buttonRole", "primary")
        open_button.setMinimumHeight(52)
        open_button.clicked.connect(self._open_scan_target)
        layout.addWidget(open_button, 2, 4)

        clear_button = QPushButton("Clear")
        clear_button.setMinimumHeight(52)
        clear_button.clicked.connect(self.scan_input.clear)
        layout.addWidget(clear_button, 2, 5)
        return panel

    def _build_action_toolbar(self) -> ActionToolbar:
        toolbar = ActionToolbar("Warehouse Actions")
        toolbar.add_button("Create Delivery Note", role="primary").clicked.connect(self._create_delivery)
        toolbar.add_button("Adjust Pallet Count").clicked.connect(self._adjust_pallet_count)
        toolbar.add_button("Assign Location").clicked.connect(self._assign_location)
        toolbar.add_button("Move Pallet").clicked.connect(self._move_pallet)
        toolbar.add_button("Mark Loaded").clicked.connect(self._mark_selected_pallet_loaded)
        toolbar.add_button("Print Remaining").clicked.connect(self._print_remaining_documents)
        toolbar.add_button("Upload Signed CMR").clicked.connect(self._upload_signed_cmr)
        return toolbar

    def _build_summary_cards(self) -> QGridLayout:
        cards_layout = QGridLayout()
        cards_layout.setHorizontalSpacing(14)
        cards_layout.setVerticalSpacing(14)
        self.summary_card_one = SummaryCard("Current Delivery", "", "", "", "info")
        self.summary_card_two = SummaryCard("Pallets Loaded", "", "", "", "info")
        self.summary_card_three = SummaryCard("Print Copies Remaining", "", "", "", "warning")
        cards_layout.addWidget(self.summary_card_one, 0, 0)
        cards_layout.addWidget(self.summary_card_two, 0, 1)
        cards_layout.addWidget(self.summary_card_three, 0, 2)
        return cards_layout
    def _build_transport_readiness_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        title_label = QLabel("Transport Readiness State")
        title_label.setObjectName("SectionTitle")
        top_row.addWidget(title_label)
        top_row.addStretch(1)
        self.transport_readiness_badge = StatusBadge("Pending", "warning")
        top_row.addWidget(self.transport_readiness_badge)
        layout.addLayout(top_row)

        helper_label = QLabel("Warehouse follows transport's readiness state. Document completeness is not decided here.")
        helper_label.setObjectName("PageSubtitle")
        helper_label.setWordWrap(True)
        layout.addWidget(helper_label)

        self.transport_readiness_grid = QGridLayout()
        self.transport_detail_labels: dict[str, QLabel] = {}
        rows = [
            "Delivery Slip",
            "Transport Status",
            "Customer",
            "Destination",
            "Carrier",
            "Expected Shipping Date",
            "Required Docs",
            "Signed CMR",
            "Corrections",
        ]
        for index, label_text in enumerate(rows):
            self.transport_readiness_grid.addWidget(self._caption(label_text), index, 0)
            value_label = QLabel("")
            value_label.setObjectName("MetaText")
            value_label.setWordWrap(True)
            self.transport_detail_labels[label_text] = value_label
            self.transport_readiness_grid.addWidget(value_label, index, 1)
        layout.addLayout(self.transport_readiness_grid)
        return panel

    def _build_signed_cmr_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        title_label = QLabel("Signed CMR Upload")
        title_label.setObjectName("SectionTitle")
        top_row.addWidget(title_label)
        top_row.addStretch(1)
        top_row.addWidget(StatusBadge("Separate Step", "info"))
        layout.addLayout(top_row)

        helper_label = QLabel("Upload signed CMR only after loading. It never replaces the original CMR.")
        helper_label.setObjectName("PageSubtitle")
        helper_label.setWordWrap(True)
        layout.addWidget(helper_label)

        self.upload_notes = QTextEdit()
        self.upload_notes.setMinimumHeight(110)
        layout.addWidget(self.upload_notes)

        actions_row = QHBoxLayout()
        upload_button = QPushButton("Upload Signed CMR")
        upload_button.setProperty("buttonRole", "primary")
        upload_button.clicked.connect(self._upload_signed_cmr)
        actions_row.addWidget(upload_button)
        open_signed_button = QPushButton("Open Existing Signed CMR")
        open_signed_button.clicked.connect(self._open_existing_signed_cmr)
        actions_row.addWidget(open_signed_button)
        actions_row.addStretch(1)
        layout.addLayout(actions_row)
        return panel

    def _build_pallets_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        title_label = QLabel("Pallets Linked To Delivery")
        title_label.setObjectName("SectionTitle")
        top_row.addWidget(title_label)
        top_row.addStretch(1)
        self.pallet_count_badge = StatusBadge("0 Linked", "info")
        top_row.addWidget(self.pallet_count_badge)
        layout.addLayout(top_row)

        self.pallets_table = DataTable()
        self.pallets_table.setColumnCount(6)
        self.pallets_table.setHorizontalHeaderLabels(["Pallet ID", "Status", "Current Location", "Pallet No.", "Ready To Load", "Last Movement"])
        self.pallets_table.itemSelectionChanged.connect(self._populate_pallet_action_fields_from_selection)
        layout.addWidget(self.pallets_table)
        return panel

    def _build_location_actions_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title_label = QLabel("Pallet Actions")
        title_label.setObjectName("SectionTitle")
        layout.addWidget(title_label)

        form_grid = QGridLayout()
        form_grid.setHorizontalSpacing(12)
        form_grid.setVerticalSpacing(10)
        self.selected_pallet_input = QLineEdit()
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("A-01-03 or Dock 2")
        self.move_reason = QComboBox()
        self.move_reason.addItems(["Stage for loading", "Relocate", "Correct location", "Load to truck"])
        form_grid.addWidget(self._caption("Selected Pallet"), 0, 0)
        form_grid.addWidget(self.selected_pallet_input, 0, 1)
        form_grid.addWidget(self._caption("Target Location"), 1, 0)
        form_grid.addWidget(self.location_input, 1, 1)
        form_grid.addWidget(self._caption("Action"), 2, 0)
        form_grid.addWidget(self.move_reason, 2, 1)
        layout.addLayout(form_grid)

        action_buttons = QVBoxLayout()
        assign_button = QPushButton("Assign Warehouse Location")
        assign_button.setProperty("buttonRole", "primary")
        assign_button.clicked.connect(self._assign_location)
        action_buttons.addWidget(assign_button)
        move_button = QPushButton("Move Pallet")
        move_button.clicked.connect(self._move_pallet)
        action_buttons.addWidget(move_button)
        load_button = QPushButton("Mark Pallet As Loaded")
        load_button.clicked.connect(self._mark_selected_pallet_loaded)
        action_buttons.addWidget(load_button)
        finalize_button = QPushButton("Finalize Shipment (Ship)")
        finalize_button.setProperty("buttonRole", "primary")
        finalize_button.clicked.connect(self._finalize_shipment)
        action_buttons.addWidget(finalize_button)
        action_buttons.addStretch(1)
        layout.addLayout(action_buttons)
        return panel

    def _build_documents_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
        self.documents_panel = panel
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title_row = QHBoxLayout()
        title_label = QLabel("Quick Document Access")
        title_label.setObjectName("SectionTitle")
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        open_all_button = QPushButton("Open All Documents")
        open_all_button.clicked.connect(self._open_all_documents)
        title_row.addWidget(open_all_button)
        layout.addLayout(title_row)

        helper_label = QLabel("Warehouse can quickly open and print the documents transport has already made ready.")
        helper_label.setObjectName("PageSubtitle")
        helper_label.setWordWrap(True)
        layout.addWidget(helper_label)

        self.document_cards_layout = QGridLayout()
        self.document_cards_layout.setHorizontalSpacing(12)
        self.document_cards_layout.setVerticalSpacing(12)
        layout.addLayout(self.document_cards_layout)
        return panel

    def _build_print_execution_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
        self.print_execution_panel = panel
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        title_label = QLabel("Print Execution")
        title_label.setObjectName("SectionTitle")
        top_row.addWidget(title_label)
        top_row.addStretch(1)
        print_all_button = QPushButton("Print Remaining")
        print_all_button.setProperty("buttonRole", "primary")
        print_all_button.clicked.connect(self._print_remaining_documents)
        top_row.addWidget(print_all_button)
        layout.addLayout(top_row)

        helper_label = QLabel("Warehouse executes printing against transport-defined requirements. Manual workstation printer override remains available.")
        helper_label.setObjectName("PageSubtitle")
        helper_label.setWordWrap(True)
        layout.addWidget(helper_label)

        self.print_execution_table = DataTable()
        self.print_execution_table.setColumnCount(6)
        self.print_execution_table.setHorizontalHeaderLabels(["Document Type", "Required", "Printed", "Remaining", "Printer", "Action State"])
        layout.addWidget(self.print_execution_table)

        action_row = QHBoxLayout()
        print_selected_button = QPushButton("Print Selected")
        print_selected_button.clicked.connect(self._print_selected_document)
        action_row.addWidget(print_selected_button)
        manual_override_button = QPushButton("Manual Printer Override")
        manual_override_button.clicked.connect(self._manual_printer_override)
        action_row.addWidget(manual_override_button)
        reprint_button = QPushButton("Reprint Last Job")
        reprint_button.clicked.connect(self._reprint_last_job)
        action_row.addWidget(reprint_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)
        return panel
    def _refresh_all(self) -> None:
        delivery = self._workflow_store.current_delivery()
        documents_ready_for_warehouse = delivery.is_ready_for_release
        delivery_changed = delivery.delivery_slip_number != self._displayed_delivery_slip_number
        self._displayed_delivery_slip_number = delivery.delivery_slip_number
        self.page_header.set_subtitle(f"{delivery.delivery_slip_number} | {delivery.customer_name} | {delivery.status.value.replace('_', ' ').title()}")
        if delivery_changed or not self.scan_input.text().strip():
            self.scan_input.setText(delivery.delivery_slip_number)
        if (delivery_changed or not self.selected_pallet_input.text().strip()) and delivery.pallets:
            self.selected_pallet_input.setText(delivery.pallets[0].pallet_id)
        if (delivery_changed or not self.location_input.text().strip()) and delivery.pallets:
            self.location_input.setText(delivery.pallets[0].current_location)
        if delivery_changed or not self.upload_notes.toPlainText().strip():
            self.upload_notes.setPlainText("Loading complete. Await signed paperwork from dock team before upload.")
        self._refresh_summary_cards(delivery)
        self._refresh_transport_readiness_panel(delivery)
        self._refresh_pallets_table(delivery)
        self.documents_panel.setVisible(documents_ready_for_warehouse)
        self.print_execution_panel.setVisible(documents_ready_for_warehouse)
        if documents_ready_for_warehouse:
            self._refresh_document_cards(delivery)
            self._refresh_print_execution_table(delivery)

    def _refresh_summary_cards(self, delivery) -> None:
        self.summary_card_one.update_content(
            "Current Delivery",
            delivery.delivery_slip_number,
            "Warehouse follows transport release state for this load",
            "Ready",
            "success" if delivery.status == DeliverySlipStatus.RELEASED_BY_TRANSPORT else "info",
        )
        self.summary_card_two.update_content(
            "Pallets Loaded",
            f"{delivery.loaded_pallets} / {delivery.total_pallets}",
            "Loaded pallets out of expected delivery total",
            "Operational",
            "info",
        )
        remaining_prints = sum(item.remaining_copies for item in delivery.print_requirements.values())
        self.summary_card_three.update_content(
            "Print Copies Remaining",
            str(remaining_prints),
            "Warehouse can still print the outstanding transport-defined copies",
            "Action",
            "warning" if remaining_prints else "success",
        )

    def _refresh_transport_readiness_panel(self, delivery) -> None:
        readiness_text = delivery.transport_readiness_text
        self.transport_readiness_badge.setText(readiness_text)
        self.transport_readiness_badge.set_tone("success" if readiness_text == "Ready" else "warning")
        self.transport_detail_labels["Delivery Slip"].setText(delivery.delivery_slip_number)
        self.transport_detail_labels["Transport Status"].setText(delivery.status.value.replace("_", " ").title())
        self.transport_detail_labels["Customer"].setText(delivery.customer_name)
        self.transport_detail_labels["Destination"].setText(delivery.destination_name)
        self.transport_detail_labels["Carrier"].setText(delivery.carrier_name or "Not set by transport")
        self.transport_detail_labels["Expected Shipping Date"].setText(
            delivery.expected_loading_date or "Not set by transport"
        )
        required_docs = ", ".join(
            item.value.replace("_", " ").title()
            for item in sorted(delivery.required_document_types, key=lambda x: x.value)
        )
        if not required_docs:
            required_docs = "No transport documents required"
        self.transport_detail_labels["Required Docs"].setText(required_docs)
        self.transport_detail_labels["Signed CMR"].setText(delivery.signed_cmr_status_text)
        self.transport_detail_labels["Corrections"].setText(
            delivery.correction_notes[-1] if delivery.correction_notes else "No corrections"
        )

    def _refresh_pallets_table(self, delivery) -> None:
        self.pallet_count_badge.setText(f"{delivery.total_pallets} Linked")
        self.pallets_table.setRowCount(len(delivery.pallets))
        for row_index, pallet in enumerate(delivery.pallets, start=1):
            values = [pallet.pallet_id, pallet.status.value.replace("_", " ").title(), pallet.current_location, str(row_index), "Yes" if pallet.ready_to_load else "No", pallet.last_movement]
            for column_index, value in enumerate(values):
                self.pallets_table.setItem(row_index - 1, column_index, QTableWidgetItem(value))
        if delivery.pallets and self.pallets_table.currentRow() < 0:
            self.pallets_table.selectRow(0)
            self._populate_pallet_action_fields_from_selection()

    def _refresh_document_cards(self, delivery) -> None:
        while self.document_cards_layout.count():
            item = self.document_cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._document_cards_by_title.clear()

        document_order = [
            DocumentType.PACKING_SLIP,
            DocumentType.CMR,
            DocumentType.CERTIFICATE,
            DocumentType.STICKER,
            DocumentType.TRANSPORT_DOCUMENT,
            DocumentType.SIGNED_CMR,
        ]
        visible_document_types: list[DocumentType] = []
        for document_type in document_order:
            record = delivery.documents.get(document_type)
            requirement = delivery.print_requirements.get(document_type)
            required_copies = requirement.required_copies if requirement is not None else 0
            is_signed_cmr_follow_up = (
                document_type == DocumentType.SIGNED_CMR and delivery.signed_cmr_expected
            )
            if record is None and required_copies == 0 and not is_signed_cmr_follow_up:
                continue
            visible_document_types.append(document_type)

        for index, document_type in enumerate(visible_document_types):
            record = delivery.documents.get(document_type)
            uploaded_count = delivery.uploaded_document_count(document_type)
            title = document_type.value.replace("_", " ").title()
            if record is None:
                filename = "Not uploaded yet"
                metadata = "Awaiting upload"
                status_text = "Pending"
                status_tone = "warning"
                can_open = False
                can_print = False
            else:
                filename = record.filename
                metadata = record.metadata_text
                if uploaded_count > 1:
                    metadata = f"{uploaded_count} files uploaded | Latest: {metadata}"
                status_text = "Available"
                status_tone = "success" if document_type != DocumentType.SIGNED_CMR else "info"
                can_open = True
                can_print = True

            if document_type == DocumentType.SIGNED_CMR and record is None:
                metadata = "Awaiting signed CMR upload after loading"
                can_print = False

            card = DocumentCard(
                title,
                filename,
                metadata,
                status_text,
                status_tone,
                can_open=can_open,
                can_print=can_print,
            )
            card.open_requested.connect(self._open_document)
            card.print_requested.connect(self._print_document)
            self._document_cards_by_title[title] = card
            self.document_cards_layout.addWidget(card, index // 2, index % 2)

    def _refresh_print_execution_table(self, delivery) -> None:
        rows = [
            row
            for row in delivery.print_requirements.values()
            if row.effective_required_copies > 0
            or row.printed_copies > 0
            or (
                row.document_type == DocumentType.SIGNED_CMR
                and delivery.signed_cmr_expected
                and delivery.signed_cmr_uploaded
            )
        ]
        self.print_execution_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            action_state = "Print now" if row.remaining_copies > 0 else "Done"
            values = [
                row.document_type.value.replace("_", " ").title(),
                str(row.effective_required_copies),
                str(row.printed_copies),
                str(row.remaining_copies),
                row.active_printer,
                action_state,
            ]
            for column_index, value in enumerate(values):
                self.print_execution_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _create_delivery(self) -> None:
        dialog = CreateDeliveryDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        delivery_slip_number = dialog.delivery_slip_input.text().strip()
        customer = dialog.customer_input.text().strip()
        destination = dialog.destination_input.text().strip()
        pallet_text = dialog.pallet_count_input.text().strip()
        if not customer or not destination or not pallet_text.isdigit():
            self._show_warning("Customer, destination, and numeric pallet count are required.")
            return
        try:
            delivery = self._workflow_store.create_delivery(
                customer,
                destination,
                int(pallet_text),
                "warehouse.operator",
                delivery_slip_number=delivery_slip_number or None,
            )
        except ValueError as error:
            self._show_warning(str(error))
            return
        self.scan_input.setText(delivery.delivery_slip_number)
        self._show_information(f"Created new delivery note {delivery.delivery_slip_number}.")

    def _adjust_pallet_count(self) -> None:
        delivery = self._workflow_store.current_delivery()
        new_count_text, accepted = QInputDialog.getText(
            self,
            "Adjust Pallet Count",
            "Correct pallet count",
            text=str(delivery.total_pallets),
        )
        if not accepted:
            return
        if not new_count_text.strip().isdigit():
            self._show_warning("Pallet count must be a number.")
            return
        try:
            self._workflow_store.adjust_pallet_count(
                delivery.delivery_slip_number,
                int(new_count_text.strip()),
                "warehouse.operator",
            )
        except ValueError as error:
            self._show_warning(str(error))
            return
        self._show_information("Pallet count corrected and sticker labels regenerated.")

    def _open_scan_target(self) -> None:
        try:
            delivery = self._workflow_store.find_delivery_by_reference(self.scan_input.text())
        except ValueError as error:
            self._show_warning(str(error))
            return
        self._workflow_store.set_current_delivery(delivery.delivery_slip_number)
        self.scan_input.setText(delivery.delivery_slip_number)
        if delivery.pallets:
            self.selected_pallet_input.setText(delivery.pallets[0].pallet_id)
            self.location_input.setText(delivery.pallets[0].current_location)

    def _assign_location(self) -> None:
        pallet_id = self.selected_pallet_input.text().strip()
        location = self.location_input.text().strip()
        if not pallet_id or not location:
            self._show_warning("Pallet and target location are required.")
            return
        try:
            self._workflow_store.assign_pallet_location(self._workflow_store.current_delivery().delivery_slip_number, pallet_id, location, "warehouse.operator")
        except ValueError as error:
            self._show_warning(str(error))
            return
        self._show_information(f"{pallet_id} assigned to {location}.")

    def _move_pallet(self) -> None:
        pallet_id = self.selected_pallet_input.text().strip()
        location = self.location_input.text().strip()
        if not pallet_id or not location:
            self._show_warning("Pallet and target location are required.")
            return
        try:
            self._workflow_store.move_pallet(self._workflow_store.current_delivery().delivery_slip_number, pallet_id, location, self.move_reason.currentText(), "warehouse.operator")
        except ValueError as error:
            self._show_warning(str(error))
            return
        self._show_information(f"{pallet_id} moved to {location}.")

    def _mark_selected_pallet_loaded(self) -> None:
        pallet_id = self.selected_pallet_input.text().strip()
        if not pallet_id:
            self._show_warning("Select a pallet first.")
            return
        try:
            self._workflow_store.mark_pallet_loaded(self._workflow_store.current_delivery().delivery_slip_number, pallet_id, "warehouse.operator")
        except ValueError as error:
            self._show_warning(str(error))
            return
        self._show_information(f"{pallet_id} marked as loaded.")

    def _finalize_shipment(self) -> None:
        delivery = self._workflow_store.current_delivery()
        summary = self._workflow_store.loading_summary(delivery.delivery_slip_number)
        if not summary["is_complete"]:
            missing = ", ".join(summary["missing_pallets"]) or "unknown"
            self._show_warning(f"Cannot finalize shipment. Missing pallets: {missing}.")
            return
        self._workflow_store.finalize_shipment(delivery.delivery_slip_number, "warehouse.operator")
        self._show_information("All pallets loaded. Shipment status changed to Shipped and moved to sent history.")

    def _upload_signed_cmr(self) -> None:
        delivery = self._workflow_store.current_delivery()
        if delivery.status not in {DeliverySlipStatus.SHIPPED, DeliverySlipStatus.COMPLETED}:
            self._show_warning("Signed CMR should be uploaded after loading and shipment completion.")
            return
        file_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Select signed CMR to upload",
            "",
            "Documents (*.pdf *.png *.jpg *.jpeg *.tif *.tiff);;All files (*.*)",
        )
        if not file_path:
            return
        filename = Path(file_path).name
        self._workflow_store.upload_document(
            delivery.delivery_slip_number,
            DocumentType.SIGNED_CMR,
            filename,
            "warehouse.operator",
            source_path=file_path,
        )
        self._show_information(f"Signed CMR uploaded for {delivery.delivery_slip_number}.")

    def _open_existing_signed_cmr(self) -> None:
        delivery = self._workflow_store.current_delivery()
        record = delivery.documents.get(DocumentType.SIGNED_CMR)
        if record is None:
            self._show_warning("No signed CMR uploaded yet.")
            return
        if record.source_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(record.source_path))
            return
        self._show_information(f"Open signed CMR: {record.filename}")

    def _open_all_documents(self) -> None:
        delivery = self._workflow_store.current_delivery()
        if not delivery.documents:
            self._show_warning("No documents available yet.")
            return
        filenames = ", ".join(record.filename for record in delivery.documents.values())
        self._show_information(f"Documents available: {filenames}")

    def _open_document(self, title: str) -> None:
        delivery = self._workflow_store.current_delivery()
        document_type = DocumentType[title.replace(" ", "_").upper()]
        record = delivery.documents.get(document_type)
        if record is None:
            self._show_warning(f"{title} has not been uploaded yet.")
            return
        if record.source_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(record.source_path))
            return
        self._show_information(f"Open document: {record.filename}")

    def _print_document(self, title: str) -> None:
        document_type = DocumentType[title.replace(" ", "_").upper()]
        if (
            document_type == DocumentType.SIGNED_CMR
            and self._workflow_store.current_delivery().documents.get(DocumentType.SIGNED_CMR) is None
        ):
            self._show_warning("Signed CMR can only be printed in warehouse after it has been uploaded.")
            return
        self._apply_print_action(document_type, reprint=False)

    def _print_remaining_documents(self) -> None:
        delivery = self._workflow_store.current_delivery()
        printed_any = False
        for document_type, requirement in delivery.print_requirements.items():
            if requirement.remaining_copies > 0:
                self._workflow_store.print_document(delivery.delivery_slip_number, document_type, requirement.remaining_copies, "warehouse.operator")
                self._last_printed_document_type = document_type
                printed_any = True
        if printed_any:
            self._show_information("Remaining required documents were sent to the configured printers.")
        else:
            self._show_information("No remaining copies needed printing.")

    def _print_selected_document(self) -> None:
        current_row = self.print_execution_table.currentRow()
        if current_row < 0:
            self._show_warning("Select a document type in the print table first.")
            return
        title = self.print_execution_table.item(current_row, 0).text()
        self._apply_print_action(DocumentType[title.replace(" ", "_").upper()], reprint=False)

    def _manual_printer_override(self) -> None:
        current_row = self.print_execution_table.currentRow()
        if current_row < 0:
            self._show_warning("Select a document type in the print table first.")
            return
        title = self.print_execution_table.item(current_row, 0).text()
        document_type = DocumentType[title.replace(" ", "_").upper()]
        dialog = BaseDialog("Manual Printer Override", f"Set a manual printer override for {title}.", self)
        printer_input = QLineEdit()
        dialog.content_layout.addWidget(printer_input)
        save_button = dialog.add_action_button("Save", role="primary")
        cancel_button = dialog.add_action_button("Cancel")
        save_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        if dialog.exec() != QDialog.DialogCode.Accepted or not printer_input.text().strip():
            return
        self._workflow_store.set_printer_override(self._workflow_store.current_delivery().delivery_slip_number, document_type, printer_input.text().strip(), "warehouse.operator")
        self._show_information(f"Printer override set for {title}.")

    def _reprint_last_job(self) -> None:
        if self._last_printed_document_type is None:
            self._show_warning("No previous print job is available for reprint.")
            return
        self._apply_print_action(self._last_printed_document_type, reprint=True)

    def _apply_print_action(self, document_type: DocumentType, reprint: bool) -> None:
        delivery = self._workflow_store.current_delivery()
        requirement = delivery.print_requirements[document_type]
        if requirement.effective_required_copies <= 0 and not reprint:
            self._show_warning(
                f"No transport print requirement is available yet for {document_type.value.replace('_', ' ').title()}."
            )
            return
        copies = 1 if reprint else max(requirement.remaining_copies, 1)
        try:
            self._workflow_store.print_document(
                delivery.delivery_slip_number,
                document_type,
                copies,
                "warehouse.operator",
                is_reprint=reprint,
            )
        except ValueError as error:
            self._show_warning(str(error))
            return
        self._last_printed_document_type = document_type
        action_text = "Reprint" if reprint else "Print"
        self._show_information(f"{action_text} sent for {document_type.value.replace('_', ' ').title()} ({copies} copies).")

    def _show_information(self, message: str) -> None:
        QMessageBox.information(self, "Warehouse", message)

    def _show_warning(self, message: str) -> None:
        QMessageBox.warning(self, "Warehouse", message)

    def _create_panel(self, object_name: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName(object_name)
        return panel

    def _caption(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionCaption")
        return label

    def _populate_pallet_action_fields_from_selection(self) -> None:
        """Mirror the selected pallet row into the action form for faster warehouse work."""
        current_row = self.pallets_table.currentRow()
        if current_row < 0:
            return

        pallet_item = self.pallets_table.item(current_row, 0)
        location_item = self.pallets_table.item(current_row, 2)
        ready_item = self.pallets_table.item(current_row, 4)
        if pallet_item is None or location_item is None or ready_item is None:
            return

        self.selected_pallet_input.setText(pallet_item.text())
        self.location_input.setText(location_item.text())
        if ready_item.text() == "Yes":
            self.move_reason.setCurrentText("Load to truck")
        elif "Dock" in location_item.text():
            self.move_reason.setCurrentText("Stage for loading")
        else:
            self.move_reason.setCurrentText("Relocate")
