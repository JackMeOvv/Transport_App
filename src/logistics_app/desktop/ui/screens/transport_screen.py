"""Transport screen for the desktop client."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTabWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from logistics_app.data.models.enums import DeliverySlipStatus, DocumentType
from logistics_app.desktop.ui.widgets import (
    ActionToolbar,
    DataTable,
    DocumentCard,
    PageHeader,
    StatusBadge,
    SummaryCard,
)
from logistics_app.desktop.workflow import DeliveryWorkflowRecord, get_workflow_store


@dataclass(slots=True)
class DocumentCardData:
    title: str
    filename: str
    metadata: str
    status_text: str
    status_tone: str


@dataclass(slots=True)
class PrintRequirementRow:
    document_type: str
    required_copies: int
    printed_copies: int
    remaining_copies: int
    default_printer: str
    readiness: str


class TransportScreenWindow(QMainWindow):
    """Transport workspace focused on queue-first work and claimed ownership."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Transport Workspace")
        self.resize(1480, 980)

        self._workflow_store = get_workflow_store()
        self._workflow_store.workflow_changed.connect(self._refresh_all)
        self._workflow_store.current_delivery_changed.connect(lambda _value: self._refresh_all())
        self._document_cards_by_title: dict[str, DocumentCard] = {}
        self._delivery_detail_labels: dict[str, QLabel] = {}
        self._readiness_checkboxes: dict[str, QCheckBox] = {}

        self.overview_tabs = QTabWidget()
        self.overview_tabs.addTab(self._build_active_shipments_page(), "Active / To Ship")
        self.overview_tabs.addTab(self._build_sent_shipments_page(), "Sent / Shipped")

        self.details_page = self._build_details_page()
        self.workspace_stack = QStackedWidget()
        self.workspace_stack.addWidget(self.overview_tabs)
        self.workspace_stack.addWidget(self.details_page)
        self.setCentralWidget(self.workspace_stack)
        self._refresh_all()

    def _build_active_shipments_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = PageHeader(
            title="Active Shipments",
            subtitle="Shipments requiring document preparation, release, or loading follow-up.",
        )
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_all)
        header.add_action_widget(refresh_button)
        layout.addWidget(header)
        layout.addWidget(self._build_delivery_search_panel())
        layout.addWidget(self._build_transport_settings_panel())

        new_orders_label = QLabel("New / In Preparation")
        new_orders_label.setObjectName("SectionTitle")
        layout.addWidget(new_orders_label)

        self.active_shipments_table = DataTable()
        self.active_shipments_table.setColumnCount(8)
        self.active_shipments_table.setHorizontalHeaderLabels(
            ["Delivery Slip", "Customer", "Destination", "Status", "Docs", "Readiness", "Claimed By", "Action"]
        )
        self.active_shipments_table.itemDoubleClicked.connect(self._open_active_row)
        layout.addWidget(self.active_shipments_table)

        released_orders_label = QLabel("Released Orders")
        released_orders_label.setObjectName("SectionTitle")
        layout.addWidget(released_orders_label)

        self.released_shipments_table = DataTable()
        self.released_shipments_table.setColumnCount(8)
        self.released_shipments_table.setHorizontalHeaderLabels(
            ["Delivery Slip", "Customer", "Destination", "Status", "Docs", "Readiness", "Claimed By", "Action"]
        )
        self.released_shipments_table.itemDoubleClicked.connect(self._open_released_row)
        layout.addWidget(self.released_shipments_table)
        return page

    def _build_sent_shipments_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = PageHeader(
            title="Sent Shipments",
            subtitle="Transport can search shipped deliveries, reopen them, and follow up on documents.",
        )
        layout.addWidget(header)

        search_layout = QHBoxLayout()
        self.sent_search_input = QLineEdit()
        self.sent_search_input.setPlaceholderText("Search shipped delivery note or customer...")
        self.sent_search_input.textChanged.connect(self._refresh_sent_shipments_table)
        search_layout.addWidget(self.sent_search_input)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.sent_search_input.clear)
        search_layout.addWidget(clear_button)
        layout.addLayout(search_layout)

        self.sent_shipments_table = DataTable()
        self.sent_shipments_table.setColumnCount(8)
        self.sent_shipments_table.setHorizontalHeaderLabels(
            ["Delivery Slip", "Customer", "Shipped", "Status", "Signed CMR", "Documents", "Claimed By", "Action"]
        )
        self.sent_shipments_table.itemDoubleClicked.connect(self._open_sent_row)
        layout.addWidget(self.sent_shipments_table)
        return page

    def _build_details_page(self) -> QWidget:
        page_root = QWidget()
        page_root.setObjectName("PageRoot")
        content_layout = QVBoxLayout(page_root)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(18)

        self.page_header = PageHeader(
            title="Shipment Details",
            subtitle="Transport opens a shipment from the overview and works that record explicitly.",
        )
        self._build_header_actions(self.page_header)
        content_layout.addWidget(self.page_header)
        content_layout.addWidget(self._build_action_toolbar())
        self.summary_cards_layout = self._build_summary_cards()
        content_layout.addLayout(self.summary_cards_layout)

        main_grid = QGridLayout()
        main_grid.setHorizontalSpacing(18)
        main_grid.setVerticalSpacing(18)
        main_grid.addWidget(self._build_delivery_details_panel(), 0, 0)
        main_grid.addWidget(self._build_readiness_panel(), 0, 1)
        main_grid.addWidget(self._build_documents_panel(), 1, 0)
        main_grid.addWidget(self._build_print_requirements_panel(), 1, 1)
        main_grid.addWidget(self._build_pallets_panel(), 2, 0)
        main_grid.addWidget(self._build_split_transport_panel(), 2, 1)
        main_grid.setColumnStretch(0, 3)
        main_grid.setColumnStretch(1, 2)
        content_layout.addLayout(main_grid)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(page_root)
        return scroll_area

    def _build_header_actions(self, page_header: PageHeader) -> None:
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_all)
        page_header.add_action_widget(refresh_button)

        open_queue_button = QPushButton("Back To Queue")
        open_queue_button.clicked.connect(lambda: self._show_overview(tab_index=0))
        page_header.add_action_widget(open_queue_button)

        sent_history_button = QPushButton("Open Sent History")
        sent_history_button.clicked.connect(lambda: self._show_overview(tab_index=1))
        page_header.add_action_widget(sent_history_button)

    def _build_transport_settings_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
        layout = QGridLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)

        title_label = QLabel("Transport Settings")
        title_label.setObjectName("SectionTitle")
        layout.addWidget(title_label, 0, 0, 1, 4)

        layout.addWidget(self._caption("Your Name"), 1, 0)
        self.operator_name_input = QLineEdit()
        self.operator_name_input.setPlaceholderText("Enter colleague name")
        self.operator_name_input.setText(self._workflow_store.transport_operator_name())
        layout.addWidget(self.operator_name_input, 1, 1)

        save_button = QPushButton("Save Name")
        save_button.setProperty("buttonRole", "primary")
        save_button.clicked.connect(self._save_transport_settings)
        layout.addWidget(save_button, 1, 2)

        self.current_operator_badge = StatusBadge("No colleague set", "warning")
        layout.addWidget(self.current_operator_badge, 1, 3)
        return panel

    def _build_delivery_search_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
        layout = QGridLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)

        title_label = QLabel("Open Main Delivery Slip")
        title_label.setObjectName("SectionTitle")
        layout.addWidget(title_label, 0, 0, 1, 6)

        layout.addWidget(self._caption("Delivery Slip"), 1, 0)
        self.slip_input = QLineEdit()
        self.slip_input.setPlaceholderText("Enter or scan delivery slip number")
        self.slip_input.setText(self._workflow_store.current_delivery().delivery_slip_number)
        layout.addWidget(self.slip_input, 1, 1, 1, 2)

        layout.addWidget(self._caption("Customer"), 1, 3)
        self.customer_filter = QComboBox()
        self.customer_filter.addItems(["All customers"] + sorted({d.customer_name for d in self._workflow_store.all_deliveries()}))
        self.customer_filter.currentIndexChanged.connect(self._refresh_active_shipments_table)
        layout.addWidget(self.customer_filter, 1, 4)

        open_button = QPushButton("Open Delivery")
        open_button.setProperty("buttonRole", "primary")
        open_button.clicked.connect(self._open_delivery_from_input)
        layout.addWidget(open_button, 1, 5)

        recent_label = QLabel("Recent")
        recent_label.setObjectName("SectionCaption")
        layout.addWidget(recent_label, 2, 0)

        recent_row = QHBoxLayout()
        recent_row.setSpacing(8)
        for delivery in self._workflow_store.active_deliveries()[:4]:
            chip = QPushButton(delivery.delivery_slip_number)
            chip.setProperty("buttonRole", "toolbar")
            chip.clicked.connect(lambda _checked=False, slip=delivery.delivery_slip_number: self._open_delivery(slip))
            recent_row.addWidget(chip)
        recent_row.addStretch(1)
        layout.addLayout(recent_row, 2, 1, 1, 5)
        return panel
    def _build_action_toolbar(self) -> ActionToolbar:
        toolbar = ActionToolbar("Transport Actions")
        toolbar.add_button("Back To Queue").clicked.connect(lambda: self._show_overview(tab_index=0))
        toolbar.add_button("Claim Shipment", role="primary").clicked.connect(self._claim_current_delivery)
        toolbar.add_button("Release Claim").clicked.connect(self._release_current_delivery_claim)
        toolbar.add_button("Upload Documents", role="primary").clicked.connect(self._upload_document)
        toolbar.add_button("Adjust Print Copies").clicked.connect(self._adjust_print_copies)
        toolbar.add_button("Confirm Readiness").clicked.connect(self._confirm_document_readiness)
        toolbar.add_button("Set Expected Shipping Date").clicked.connect(self._set_expected_shipping_date)
        toolbar.add_button("Open Sent History").clicked.connect(lambda: self._show_overview(tab_index=1))
        return toolbar

    def _build_summary_cards(self) -> QGridLayout:
        cards_layout = QGridLayout()
        cards_layout.setHorizontalSpacing(14)
        cards_layout.setVerticalSpacing(14)
        self.summary_card_slot_one = SummaryCard("Current Status", "", "", "", "info")
        self.summary_card_slot_two = SummaryCard("Document Completeness", "", "", "", "warning")
        self.summary_card_slot_three = SummaryCard("Remaining Prints", "", "", "", "info")
        cards_layout.addWidget(self.summary_card_slot_one, 0, 0)
        cards_layout.addWidget(self.summary_card_slot_two, 0, 1)
        cards_layout.addWidget(self.summary_card_slot_three, 0, 2)
        return cards_layout

    def _build_delivery_details_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        title_label = QLabel("Delivery Details")
        title_label.setObjectName("SectionTitle")
        layout.addWidget(title_label)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        fields = [
            "Delivery Slip",
            "Transport Ref",
            "Customer",
            "Delivery Date",
            "Origin",
            "Destination",
            "Status",
            "Expected Shipping Date",
            "Shipped At",
            "Claimed By",
            "Corrections",
        ]
        for index, label in enumerate(fields):
            row = index // 2
            column = (index % 2) * 2
            grid.addWidget(self._caption(label), row, column)
            value_label = QLabel("")
            value_label.setObjectName("MetaText")
            value_label.setWordWrap(True)
            self._delivery_detail_labels[label] = value_label
            grid.addWidget(value_label, row, column + 1)
        layout.addLayout(grid)

        notes_label = QLabel("Transport Notes")
        notes_label.setObjectName("SectionCaption")
        layout.addWidget(notes_label)
        self.notes_box = QTextEdit()
        self.notes_box.setMinimumHeight(100)
        self.notes_box.textChanged.connect(self._update_transport_notes)
        layout.addWidget(self.notes_box)
        return panel

    def _build_readiness_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        title_label = QLabel("Document Readiness")
        title_label.setObjectName("SectionTitle")
        top_row.addWidget(title_label)
        top_row.addStretch(1)
        self.readiness_status_badge = StatusBadge("Pending", "warning")
        top_row.addWidget(self.readiness_status_badge)
        layout.addLayout(top_row)

        summary_label = QLabel(
            "Transport controls document completeness. The checklist supports the transport decision "
            "and does not block release."
        )
        summary_label.setObjectName("PageSubtitle")
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        checklist_group = QGroupBox("Readiness Checklist")
        checklist_layout = QVBoxLayout(checklist_group)
        checklist_layout.setContentsMargins(16, 16, 16, 16)
        checklist_layout.setSpacing(10)
        for key, text in [
            ("packing_slip", "Packing slip uploaded"),
            ("cmr", "CMR uploaded"),
            ("certificate", "Certificate uploaded"),
            ("sticker", "Sticker uploaded"),
            ("print_copies", "Print copies defined"),
            ("signed_cmr", "Signed CMR expected after loading"),
            ("release", "Transport confirms release to warehouse"),
        ]:
            checkbox = QCheckBox(text)
            checkbox.setEnabled(False)
            self._readiness_checkboxes[key] = checkbox
            checklist_layout.addWidget(checkbox)
        layout.addWidget(checklist_group)

        confirm_button = QPushButton("Confirm Document Readiness")
        confirm_button.setProperty("buttonRole", "primary")
        confirm_button.clicked.connect(self._confirm_document_readiness)
        layout.addWidget(confirm_button)
        return panel

    def _build_documents_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title_row = QHBoxLayout()
        title_label = QLabel("Documents")
        title_label.setObjectName("SectionTitle")
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        upload_button = QPushButton("Upload Document")
        upload_button.setProperty("buttonRole", "primary")
        upload_button.clicked.connect(self._upload_document)
        title_row.addWidget(upload_button)
        layout.addLayout(title_row)

        helper_text = QLabel("Transport maintains the authoritative document set for the delivery. Signed CMR remains a separate document type.")
        helper_text.setObjectName("PageSubtitle")
        helper_text.setWordWrap(True)
        layout.addWidget(helper_text)

        self.document_cards_layout = QGridLayout()
        self.document_cards_layout.setHorizontalSpacing(12)
        self.document_cards_layout.setVerticalSpacing(12)
        layout.addLayout(self.document_cards_layout)
        return panel

    def _build_print_requirements_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        title_label = QLabel("Print Requirements")
        title_label.setObjectName("SectionTitle")
        top_row.addWidget(title_label)
        top_row.addStretch(1)
        edit_button = QPushButton("Edit Requirements")
        edit_button.setProperty("buttonRole", "primary")
        edit_button.clicked.connect(self._adjust_print_copies)
        top_row.addWidget(edit_button)
        layout.addLayout(top_row)

        self.print_requirements_table = DataTable()
        self.print_requirements_table.setColumnCount(6)
        self.print_requirements_table.setHorizontalHeaderLabels(["Document Type", "Required", "Printed", "Remaining", "Default Printer", "Readiness"])
        self.print_requirements_table.itemDoubleClicked.connect(lambda _item: self._adjust_print_copies())
        layout.addWidget(self.print_requirements_table)
        return panel

    def _build_pallets_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        title_label = QLabel("Linked Pallets")
        title_label.setObjectName("SectionTitle")
        top_row.addWidget(title_label)
        top_row.addStretch(1)
        self.pallet_summary_badge = StatusBadge("0 Pallets Linked", "info")
        top_row.addWidget(self.pallet_summary_badge)
        layout.addLayout(top_row)

        helper_text = QLabel("Transport can review pallet linkage here. Warehouse remains responsible for physical location handling and loading.")
        helper_text.setObjectName("PageSubtitle")
        helper_text.setWordWrap(True)
        layout.addWidget(helper_text)

        self.pallets_table = DataTable()
        self.pallets_table.setColumnCount(5)
        self.pallets_table.setHorizontalHeaderLabels(["Pallet ID", "Status", "Location", "Packages", "Last Movement"])
        layout.addWidget(self.pallets_table)
        return panel

    def _build_split_transport_panel(self) -> QGroupBox:
        group_box = QGroupBox("Rare Split Transport Handling")
        group_box.setCheckable(True)
        group_box.setChecked(False)
        layout = QVBoxLayout(group_box)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        helper_text = QLabel("This remains a secondary exception flow. The main transport workflow stays centered on one delivery slip.")
        helper_text.setObjectName("PageSubtitle")
        helper_text.setWordWrap(True)
        layout.addWidget(helper_text)

        split_table = DataTable()
        split_table.setColumnCount(4)
        split_table.setHorizontalHeaderLabels(["Split Code", "Transport Ref", "Assigned Pallets", "Document Scope"])
        split_table.setRowCount(0)
        layout.addWidget(split_table)

        actions_row = QHBoxLayout()
        actions_row.addStretch(1)
        add_split_button = QPushButton("Add Split Group")
        add_split_button.clicked.connect(self._show_split_message)
        actions_row.addWidget(add_split_button)
        review_split_button = QPushButton("Review Split Assignment")
        review_split_button.clicked.connect(self._show_split_message)
        actions_row.addWidget(review_split_button)
        layout.addLayout(actions_row)
        return group_box
    def _refresh_all(self) -> None:
        self._refresh_active_shipments_table()
        self._refresh_sent_shipments_table()
        self._refresh_details_page()
        self._refresh_operator_settings()

    def _refresh_active_shipments_table(self) -> None:
        deliveries = self._workflow_store.transport_new_deliveries()
        customer_filter = self.customer_filter.currentText() if hasattr(self, "customer_filter") else "All customers"
        if customer_filter != "All customers":
            deliveries = [delivery for delivery in deliveries if delivery.customer_name == customer_filter]
        self.active_shipments_table.setRowCount(len(deliveries))
        self._active_rows = deliveries
        for row_index, delivery in enumerate(deliveries):
            doc_count = self._document_completeness_text(delivery)
            values = [
                delivery.delivery_slip_number,
                delivery.customer_name,
                delivery.destination_name,
                delivery.status.value.replace("_", " ").title(),
                doc_count,
                delivery.transport_readiness_text,
                delivery.claimed_by or "-",
            ]
            for column_index, value in enumerate(values):
                self.active_shipments_table.setItem(row_index, column_index, QTableWidgetItem(value))
            action_button = QPushButton("Open")
            action_button.setProperty("buttonRole", "primary")
            action_button.clicked.connect(
                lambda _checked=False, slip=delivery.delivery_slip_number: self._open_delivery(slip)
            )
            self.active_shipments_table.setCellWidget(row_index, 7, action_button)

        released_deliveries = self._workflow_store.released_deliveries()
        if customer_filter != "All customers":
            released_deliveries = [
                delivery for delivery in released_deliveries if delivery.customer_name == customer_filter
            ]
        self.released_shipments_table.setRowCount(len(released_deliveries))
        self._released_rows = released_deliveries
        for row_index, delivery in enumerate(released_deliveries):
            doc_count = self._document_completeness_text(delivery)
            values = [
                delivery.delivery_slip_number,
                delivery.customer_name,
                delivery.destination_name,
                delivery.status.value.replace("_", " ").title(),
                doc_count,
                delivery.transport_readiness_text,
                delivery.claimed_by or "-",
            ]
            for column_index, value in enumerate(values):
                self.released_shipments_table.setItem(row_index, column_index, QTableWidgetItem(value))
            action_button = QPushButton("Open")
            action_button.setProperty("buttonRole", "primary")
            action_button.clicked.connect(
                lambda _checked=False, slip=delivery.delivery_slip_number: self._open_delivery(slip)
            )
            self.released_shipments_table.setCellWidget(row_index, 7, action_button)

    def _refresh_sent_shipments_table(self) -> None:
        deliveries = self._workflow_store.sent_deliveries()
        search_text = self.sent_search_input.text().strip().lower() if hasattr(self, "sent_search_input") else ""
        if search_text:
            deliveries = [delivery for delivery in deliveries if search_text in delivery.delivery_slip_number.lower() or search_text in delivery.customer_name.lower() or search_text in delivery.destination_name.lower()]
        self.sent_shipments_table.setRowCount(len(deliveries))
        self._sent_rows = deliveries
        for row_index, delivery in enumerate(deliveries):
            values = [
                delivery.delivery_slip_number,
                delivery.customer_name,
                delivery.shipped_at or "Shipped",
                delivery.status.value.replace("_", " ").title(),
                delivery.signed_cmr_status_text,
                str(len(delivery.documents)),
                delivery.claimed_by or "-",
            ]
            for column_index, value in enumerate(values):
                self.sent_shipments_table.setItem(row_index, column_index, QTableWidgetItem(value))
            action_button = QPushButton("Open")
            action_button.setProperty("buttonRole", "primary")
            action_button.clicked.connect(
                lambda _checked=False, slip=delivery.delivery_slip_number: self._open_delivery(slip)
            )
            self.sent_shipments_table.setCellWidget(row_index, 7, action_button)

    def _refresh_details_page(self) -> None:
        delivery = self._workflow_store.current_delivery()
        self.page_header.set_subtitle(f"{delivery.delivery_slip_number} | {delivery.customer_name} | {delivery.status.value.replace('_', ' ').title()}")
        detail_values = {
            "Delivery Slip": delivery.delivery_slip_number,
            "Transport Ref": delivery.transport_reference,
            "Customer": delivery.customer_name,
            "Delivery Date": delivery.delivery_date,
            "Origin": delivery.origin_name,
            "Destination": delivery.destination_name,
            "Status": delivery.status.value.replace("_", " ").title(),
            "Expected Shipping Date": delivery.expected_loading_date or "Not set",
            "Shipped At": delivery.shipped_at or "Not shipped",
            "Claimed By": delivery.claimed_by or "Unclaimed",
            "Corrections": delivery.correction_notes[-1] if delivery.correction_notes else "No corrections",
        }
        for key, value in detail_values.items():
            self._delivery_detail_labels[key].setText(value)
        self.notes_box.blockSignals(True)
        self.notes_box.setPlainText(delivery.transport_notes)
        self.notes_box.blockSignals(False)
        self._update_summary_cards(delivery)
        self._refresh_readiness_panel(delivery)
        self._refresh_documents_panel(delivery)
        self._refresh_print_requirements_table(delivery)
        self._refresh_pallets_table(delivery)
        self.slip_input.setText(delivery.delivery_slip_number)

    def _update_summary_cards(self, delivery: DeliveryWorkflowRecord) -> None:
        current_status_tone = "warning" if delivery.correction_notes else "info"
        current_status_badge = "Correction" if delivery.correction_notes else "Live"
        required_uploaded_count = self._required_uploaded_count(delivery)
        required_document_count = len(delivery.required_document_types)
        self.summary_card_slot_one.update_content(
            "Current Status",
            delivery.status.value.replace("_", " ").title(),
            "Transport workflow state for this delivery",
            delivery.claimed_by or current_status_badge,
            current_status_tone,
        )
        self.summary_card_slot_two.update_content(
            "Document Completeness",
            f"{required_uploaded_count} / {required_document_count}",
            "Checklist view of the current transport document set",
            "Check",
            "success" if delivery.status in {DeliverySlipStatus.RELEASED_BY_TRANSPORT, DeliverySlipStatus.LOADING_IN_PROGRESS, DeliverySlipStatus.SHIPPED, DeliverySlipStatus.COMPLETED} else ("warning" if not delivery.is_ready_for_release else "success"),
        )
        remaining_prints = sum(item.remaining_copies for item in delivery.print_requirements.values())
        self.summary_card_slot_three.update_content(
            "Remaining Prints",
            str(remaining_prints),
            "Transport-defined copies still awaiting warehouse printing",
            "Operational",
            "warning" if remaining_prints else "success",
        )

    def _refresh_operator_settings(self) -> None:
        if not hasattr(self, "operator_name_input"):
            return
        operator_name = self._workflow_store.transport_operator_name()
        self.operator_name_input.blockSignals(True)
        self.operator_name_input.setText(operator_name)
        self.operator_name_input.blockSignals(False)
        if operator_name:
            self.current_operator_badge.setText(operator_name)
            self.current_operator_badge.set_tone("success")
        else:
            self.current_operator_badge.setText("No colleague set")
            self.current_operator_badge.set_tone("warning")

    def _required_uploaded_count(self, delivery: DeliveryWorkflowRecord) -> int:
        return sum(1 for document_type in delivery.required_document_types if document_type in delivery.documents)

    def _document_completeness_text(self, delivery: DeliveryWorkflowRecord) -> str:
        return f"{self._required_uploaded_count(delivery)}/{len(delivery.required_document_types)}"

    def _refresh_readiness_panel(self, delivery: DeliveryWorkflowRecord) -> None:
        self.readiness_status_badge.setText(delivery.transport_readiness_text)
        self.readiness_status_badge.set_tone("success" if delivery.transport_readiness_text == "Ready" else "warning")
        available = delivery.available_document_types
        self._readiness_checkboxes["packing_slip"].setChecked(DocumentType.PACKING_SLIP in available)
        self._readiness_checkboxes["cmr"].setChecked(DocumentType.CMR in available)
        self._readiness_checkboxes["certificate"].setChecked(DocumentType.CERTIFICATE in available)
        self._readiness_checkboxes["sticker"].setChecked(DocumentType.STICKER in available)
        self._readiness_checkboxes["print_copies"].setChecked(all(req.required_copies >= 0 for req in delivery.print_requirements.values()))
        self._readiness_checkboxes["signed_cmr"].setChecked(delivery.signed_cmr_expected)
        self._readiness_checkboxes["release"].setChecked(delivery.status in {DeliverySlipStatus.RELEASED_BY_TRANSPORT, DeliverySlipStatus.LOADING_IN_PROGRESS, DeliverySlipStatus.SHIPPED, DeliverySlipStatus.COMPLETED})

    def _refresh_documents_panel(self, delivery: DeliveryWorkflowRecord) -> None:
        while self.document_cards_layout.count():
            item = self.document_cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._document_cards_by_title.clear()

        transport_document_types = [
            DocumentType.PACKING_SLIP,
            DocumentType.CMR,
            DocumentType.CERTIFICATE,
            DocumentType.STICKER,
            DocumentType.TRANSPORT_DOCUMENT,
            DocumentType.OTHER,
            DocumentType.SIGNED_CMR,
        ]
        visible_document_types: list[DocumentType] = []
        for document_type in transport_document_types:
            record = delivery.documents.get(document_type)
            requirement = delivery.print_requirements.get(document_type)
            required_copies = requirement.required_copies if requirement is not None else 0
            if record is None and required_copies == 0:
                continue
            visible_document_types.append(document_type)

        for index, document_type in enumerate(visible_document_types):
            record = delivery.documents.get(document_type)
            uploaded_count = delivery.uploaded_document_count(document_type)
            if record is None:
                title = document_type.value.replace("_", " ").title()
                filename = "Not uploaded yet"
                metadata = "Awaiting upload"
                status_text = "Pending"
                status_tone = "warning"
            else:
                title = record.title
                filename = record.filename
                metadata = record.metadata_text
                if uploaded_count > 1:
                    metadata = f"{uploaded_count} files uploaded | Latest: {metadata}"
                status_text = "Available"
                status_tone = "success" if document_type != DocumentType.SIGNED_CMR else "info"
            card = DocumentCard(title, filename, metadata, status_text, status_tone)
            card.open_requested.connect(self._open_document)
            card.print_requested.connect(self._print_document)
            self._document_cards_by_title[title] = card
            self.document_cards_layout.addWidget(card, index // 2, index % 2)

    def _refresh_print_requirements_table(self, delivery: DeliveryWorkflowRecord) -> None:
        rows = list(delivery.print_requirements.values())
        self.print_requirements_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            readiness = (
                f"{row.required_copies} each x {row.document_instances} file(s)"
                if row.required_copies > 0
                else "Optional / none"
            )
            values = [
                row.document_type.value.replace("_", " ").title(),
                str(row.required_copies),
                str(row.printed_copies),
                str(row.remaining_copies),
                row.active_printer,
                readiness,
            ]
            for column_index, value in enumerate(values):
                self.print_requirements_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _refresh_pallets_table(self, delivery: DeliveryWorkflowRecord) -> None:
        self.pallet_summary_badge.setText(f"{delivery.total_pallets} Pallets Linked")
        self.pallets_table.setRowCount(len(delivery.pallets))
        for row_index, pallet in enumerate(delivery.pallets):
            values = [pallet.pallet_id, pallet.status.value.replace("_", " ").title(), pallet.current_location, str(pallet.packages), pallet.last_movement]
            for column_index, value in enumerate(values):
                self.pallets_table.setItem(row_index, column_index, QTableWidgetItem(value))
    def _open_delivery_from_input(self) -> None:
        try:
            delivery = self._workflow_store.find_delivery_by_reference(self.slip_input.text())
        except ValueError as error:
            self._show_warning(str(error))
            return
        self._open_delivery(delivery.delivery_slip_number)

    def _open_delivery(self, delivery_slip_number: str) -> None:
        self._workflow_store.set_current_delivery(delivery_slip_number)
        self.workspace_stack.setCurrentWidget(self.details_page)

    def _show_overview(self, tab_index: int = 0) -> None:
        self.overview_tabs.setCurrentIndex(tab_index)
        self.workspace_stack.setCurrentWidget(self.overview_tabs)

    def show_default_overview(self) -> None:
        """Return transport to the queue-first view when the workspace is opened."""
        self._show_overview(tab_index=0)

    def _open_active_row(self, item: QTableWidgetItem) -> None:
        row = item.row()
        if row < len(getattr(self, "_active_rows", [])):
            self._open_delivery(self._active_rows[row].delivery_slip_number)

    def _open_sent_row(self, item: QTableWidgetItem) -> None:
        row = item.row()
        if row < len(getattr(self, "_sent_rows", [])):
            self._open_delivery(self._sent_rows[row].delivery_slip_number)

    def _open_released_row(self, item: QTableWidgetItem) -> None:
        row = item.row()
        if row < len(getattr(self, "_released_rows", [])):
            self._open_delivery(self._released_rows[row].delivery_slip_number)

    def _upload_document(self) -> None:
        delivery = self._workflow_store.current_delivery()
        document_names = [
            item.value.replace("_", " ").title()
            for item in DocumentType
            if item != DocumentType.SIGNED_CMR
        ]
        selected_name, accepted = QInputDialog.getItem(self, "Upload Document", "Document type", document_names, 0, False)
        if not accepted:
            return
        file_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Select document to upload",
            "",
            "Documents (*.pdf *.doc *.docx *.png *.jpg *.jpeg *.zpl *.txt);;All files (*.*)",
        )
        if not file_path:
            return
        document_type = DocumentType[selected_name.replace(" ", "_").upper()]
        filename = Path(file_path).name
        self._workflow_store.upload_document(
            delivery.delivery_slip_number,
            document_type,
            filename,
            "transport.office",
            source_path=file_path,
        )
        self._show_information(f"{selected_name} uploaded for {delivery.delivery_slip_number}.")

    def _save_transport_settings(self) -> None:
        self._workflow_store.set_transport_operator_name(self.operator_name_input.text())
        if self._workflow_store.transport_operator_name():
            self._show_information("Transport colleague name saved.")
        else:
            self._show_warning("Enter a colleague name so claims can be tracked.")

    def _claim_current_delivery(self) -> None:
        delivery = self._workflow_store.current_delivery()
        try:
            self._workflow_store.claim_delivery(
                delivery.delivery_slip_number,
                self._workflow_store.transport_operator_name(),
            )
        except ValueError as error:
            self._show_warning(str(error))
            return
        self._show_information(f"{delivery.delivery_slip_number} claimed successfully.")

    def _release_current_delivery_claim(self) -> None:
        delivery = self._workflow_store.current_delivery()
        try:
            self._workflow_store.release_delivery_claim(
                delivery.delivery_slip_number,
                self._workflow_store.transport_operator_name(),
            )
        except ValueError as error:
            self._show_warning(str(error))
            return
        self._show_information(f"Claim released for {delivery.delivery_slip_number}.")

    def _adjust_print_copies(self) -> None:
        delivery = self._workflow_store.current_delivery()
        current_row = self.print_requirements_table.currentRow()
        document_type: DocumentType | None = None
        selected_name = ""
        if current_row >= 0 and self.print_requirements_table.item(current_row, 0) is not None:
            selected_name = self.print_requirements_table.item(current_row, 0).text()
            document_type = DocumentType[selected_name.replace(" ", "_").upper()]
        else:
            document_names = [item.value.replace("_", " ").title() for item in delivery.print_requirements]
            selected_name, accepted = QInputDialog.getItem(self, "Adjust Print Copies", "Document type", document_names, 0, False)
            if not accepted:
                return
            document_type = DocumentType[selected_name.replace(" ", "_").upper()]
        current = delivery.print_requirements[document_type].required_copies
        required_copies, accepted = QInputDialog.getInt(self, "Adjust Print Copies", "Required copies", current, 0, 99)
        if not accepted:
            return
        self._workflow_store.set_required_copies(delivery.delivery_slip_number, document_type, required_copies, "transport.office")
        self._show_information(f"Required copies updated for {selected_name}.")

    def _confirm_document_readiness(self) -> None:
        delivery = self._workflow_store.current_delivery()
        self._workflow_store.release_delivery(delivery.delivery_slip_number, "transport.office")
        self._show_information(f"{delivery.delivery_slip_number} released to warehouse.")

    def _set_expected_shipping_date(self) -> None:
        delivery = self._workflow_store.current_delivery()
        date_value, accepted = QInputDialog.getText(
            self,
            "Expected Shipping Date",
            "Expected shipping date (YYYY-MM-DD)",
            text=delivery.expected_loading_date or delivery.delivery_date,
        )
        if not accepted or not date_value.strip():
            return
        self._workflow_store.set_expected_loading_date(
            delivery.delivery_slip_number,
            date_value.strip(),
            "transport.office",
        )
        self._show_information(f"Expected shipping date set to {date_value.strip()}.")

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
        delivery = self._workflow_store.current_delivery()
        document_type = DocumentType[title.replace(" ", "_").upper()]
        requirement = delivery.print_requirements[document_type]
        copies = max(requirement.remaining_copies, 1)
        self._workflow_store.print_document(delivery.delivery_slip_number, document_type, copies, "transport.office")
        self._show_information(f"Print request sent for {title} ({copies} copies).")

    def _show_split_message(self) -> None:
        self._show_information("Split shipment handling remains available as an exception, but it is not part of the default daily workflow.")

    def _update_transport_notes(self) -> None:
        delivery = self._workflow_store.current_delivery()
        delivery.transport_notes = self.notes_box.toPlainText().strip()

    def _show_information(self, message: str) -> None:
        QMessageBox.information(self, "Transport", message)

    def _show_warning(self, message: str) -> None:
        QMessageBox.warning(self, "Transport", message)

    def _create_panel(self, object_name: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName(object_name)
        return panel

    def _caption(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionCaption")
        return label
