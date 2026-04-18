"""Shipment overview screen for active delivery monitoring."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from logistics_app.data.models.enums import DeliverySlipStatus
from logistics_app.desktop.ui.dialogs import BaseDialog
from logistics_app.desktop.ui.widgets import ActionToolbar, DataTable, PageHeader, StatusBadge, SummaryCard
from logistics_app.desktop.workflow import DeliveryWorkflowRecord, get_workflow_store


@dataclass(frozen=True, slots=True)
class ShipmentOverviewRow:
    """Display model for the overview grid."""

    delivery_slip_number: str
    customer_name: str
    destination_name: str
    status_text: str
    status_tone: str
    pallet_count: int
    loading_progress_percent: int
    warehouse_situation: str
    warehouse_tone: str
    document_readiness_text: str
    document_readiness_tone: str
    signed_cmr_status_text: str
    signed_cmr_status_tone: str
    is_split_exception: bool


class DeliverySlipQuickViewDialog(BaseDialog):
    """Compact dialog for a quick operational delivery review."""

    def __init__(self, delivery: DeliveryWorkflowRecord, parent: QWidget | None = None) -> None:
        super().__init__(
            title=f"Delivery {delivery.delivery_slip_number}",
            message="Fast operational summary for warehouse and transport handoff.",
            parent=parent,
        )
        self.resize(620, 360)

        details_grid = QGridLayout()
        details_grid.setHorizontalSpacing(16)
        details_grid.setVerticalSpacing(10)

        summary_rows = [
            ("Customer", delivery.customer_name),
            ("Destination", delivery.destination_name),
            ("Status", delivery.status.value.replace("_", " ").title()),
            ("Pallets", str(delivery.total_pallets)),
            ("Loaded", str(delivery.loaded_pallets)),
            ("Readiness", delivery.transport_readiness_text),
            ("Signed CMR", delivery.signed_cmr_status_text),
            ("Shipped At", delivery.shipped_at or "Not shipped"),
        ]
        for index, (label_text, value_text) in enumerate(summary_rows):
            details_grid.addWidget(self._caption(label_text), index, 0)
            details_grid.addWidget(self._value(value_text), index, 1)

        self.content_layout.addLayout(details_grid)
        close_button = self.add_action_button("Close", role="primary")
        close_button.clicked.connect(self.accept)

    def _caption(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionCaption")
        return label

    def _value(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionTitle")
        label.setWordWrap(True)
        return label


class ShipmentOverviewScreenWindow(QMainWindow):
    """Operational dashboard for deliveries that are still in process."""

    open_in_warehouse_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Shipment Overview")
        self.resize(1500, 980)

        self._workflow_store = get_workflow_store()
        self._workflow_store.workflow_changed.connect(self._refresh_table)
        self._workflow_store.current_delivery_changed.connect(lambda _value: self._refresh_table())
        self._visible_rows: list[ShipmentOverviewRow] = []

        page_root = QWidget()
        page_root.setObjectName("PageRoot")

        content_layout = QVBoxLayout(page_root)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(18)

        page_header = PageHeader(
            title="Shipment Overview",
            subtitle=(
                "Active delivery slips still in process. Shipped deliveries leave this queue "
                "and move to the sent workflow in Transport."
            ),
        )
        self._build_header_actions(page_header)
        content_layout.addWidget(page_header)

        content_layout.addWidget(self._build_filter_panel())
        content_layout.addWidget(self._build_action_toolbar())
        content_layout.addLayout(self._build_summary_cards())

        main_grid = QGridLayout()
        main_grid.setHorizontalSpacing(18)
        main_grid.setVerticalSpacing(18)
        main_grid.addWidget(self._build_open_deliveries_panel(), 0, 0)
        main_grid.addWidget(self._build_queue_context_panel(), 0, 1)
        main_grid.setColumnStretch(0, 3)
        main_grid.setColumnStretch(1, 1)
        content_layout.addLayout(main_grid)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(page_root)
        self.setCentralWidget(scroll_area)

        self._refresh_table()

    def _build_header_actions(self, page_header: PageHeader) -> None:
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_table)
        page_header.add_action_widget(refresh_button)

        open_button = QPushButton("Open Delivery")
        open_button.setProperty("buttonRole", "primary")
        open_button.clicked.connect(self._open_selected_delivery)
        page_header.add_action_widget(open_button)

    def _build_filter_panel(self) -> QFrame:
        panel = self._create_panel()
        layout = QGridLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(10)

        title_label = QLabel("Filter Active Deliveries")
        title_label.setObjectName("SectionTitle")
        layout.addWidget(title_label, 0, 0, 1, 8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search delivery slip, customer, destination, or pallet reference")
        self.search_input.textChanged.connect(self._refresh_table)

        self.status_filter = QComboBox()
        self.status_filter.addItems(
            [
                "All statuses",
                "Created",
                "Stored",
                "Documents In Preparation",
                "Released By Transport",
                "Loading In Progress",
            ]
        )
        self.status_filter.currentIndexChanged.connect(self._refresh_table)

        self.readiness_filter = QComboBox()
        self.readiness_filter.addItems(["All readiness states", "Ready", "Pending Release", "Pending Documents"])
        self.readiness_filter.currentIndexChanged.connect(self._refresh_table)

        self.warehouse_filter = QComboBox()
        self.warehouse_filter.addItems(["All warehouse states", "Awaiting Action", "Staged", "Loading Now"])
        self.warehouse_filter.currentIndexChanged.connect(self._refresh_table)

        self.sort_filter = QComboBox()
        self.sort_filter.addItems(
            [
                "Sort: Delivery slip",
                "Sort: Destination",
                "Sort: Loading progress",
                "Sort: Pallet count",
            ]
        )
        self.sort_filter.currentIndexChanged.connect(self._refresh_table)

        layout.addWidget(self._caption("Search"), 1, 0)
        layout.addWidget(self.search_input, 1, 1, 1, 3)
        layout.addWidget(self._caption("Status"), 1, 4)
        layout.addWidget(self.status_filter, 1, 5)
        layout.addWidget(self._caption("Readiness"), 1, 6)
        layout.addWidget(self.readiness_filter, 1, 7)
        layout.addWidget(self._caption("Warehouse"), 2, 0)
        layout.addWidget(self.warehouse_filter, 2, 1)
        layout.addWidget(self._caption("Sort"), 2, 2)
        layout.addWidget(self.sort_filter, 2, 3)

        clear_button = QPushButton("Clear Filters")
        clear_button.clicked.connect(self._clear_filters)
        layout.addWidget(clear_button, 2, 7)
        return panel

    def _build_action_toolbar(self) -> ActionToolbar:
        toolbar = ActionToolbar("Overview Actions")
        toolbar.add_button("Open Selected Delivery", role="primary").clicked.connect(self._open_selected_delivery)
        toolbar.add_button("Quick Delivery View").clicked.connect(self._open_selected_delivery)
        toolbar.add_button("Clear Filters").clicked.connect(self._clear_filters)
        toolbar.add_button("Refresh Queue").clicked.connect(self._refresh_table)
        return toolbar

    def _build_summary_cards(self) -> QGridLayout:
        cards_layout = QGridLayout()
        cards_layout.setHorizontalSpacing(14)
        cards_layout.setVerticalSpacing(14)
        self.open_deliveries_card = SummaryCard(
            "Open Deliveries",
            "0",
            "Daily working set focused on outbound deliveries still in process",
            "Operational",
            "info",
        )
        self.released_deliveries_card = SummaryCard(
            "Released To Warehouse",
            "0",
            "Transport-ready deliveries visible for warehouse execution",
            "Ready",
            "success",
        )
        self.attention_needed_card = SummaryCard(
            "Attention Needed",
            "0",
            "Deliveries with missing documents or active loading work",
            "Watch",
            "warning",
        )
        cards_layout.addWidget(self.open_deliveries_card, 0, 0)
        cards_layout.addWidget(self.released_deliveries_card, 0, 1)
        cards_layout.addWidget(self.attention_needed_card, 0, 2)
        return cards_layout

    def _build_open_deliveries_panel(self) -> QFrame:
        panel = self._create_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title_row = QHBoxLayout()
        title_label = QLabel("Warehouse Shipment Overview")
        title_label.setObjectName("SectionTitle")
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        title_row.addWidget(StatusBadge("Common Flow First", "info"))
        layout.addLayout(title_row)

        helper_text = QLabel(
            "This screen is split into two practical queues: shipments not ready yet, and shipments already "
            "released by transport for warehouse handling."
        )
        helper_text.setObjectName("PageSubtitle")
        helper_text.setWordWrap(True)
        layout.addWidget(helper_text)

        released_label = QLabel("Released By Transport")
        released_label.setObjectName("SectionTitle")
        layout.addWidget(released_label)

        self.released_table = DataTable()
        self.released_table.setColumnCount(10)
        self.released_table.setHorizontalHeaderLabels(
            [
                "Delivery Slip",
                "Customer",
                "Destination",
                "Status",
                "Pallets",
                "Loading",
                "Warehouse",
                "Transport Readiness",
                "Signed CMR",
                "Open",
            ]
        )
        self.released_table.itemDoubleClicked.connect(self._open_released_delivery_from_row)
        layout.addWidget(self.released_table)

        not_ready_label = QLabel("Shipments Not Ready Yet")
        not_ready_label.setObjectName("SectionTitle")
        layout.addWidget(not_ready_label)

        self.not_ready_table = DataTable()
        self.not_ready_table.setColumnCount(10)
        self.not_ready_table.setHorizontalHeaderLabels(
            [
                "Delivery Slip",
                "Customer",
                "Destination",
                "Status",
                "Pallets",
                "Loading",
                "Warehouse",
                "Transport Readiness",
                "Signed CMR",
                "Open",
            ]
        )
        self.not_ready_table.itemDoubleClicked.connect(self._open_not_ready_delivery_from_row)
        layout.addWidget(self.not_ready_table)
        return panel

    def _build_queue_context_panel(self) -> QFrame:
        panel = self._create_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        section_title = QLabel("Operational Situation")
        section_title.setObjectName("SectionTitle")
        layout.addWidget(section_title)

        active = self._workflow_store.active_deliveries()
        loading_now = sum(1 for delivery in active if delivery.status == DeliverySlipStatus.LOADING_IN_PROGRESS)
        signed_pending = sum(1 for delivery in self._workflow_store.sent_deliveries() if not delivery.signed_cmr_uploaded)
        split_count = sum(1 for delivery in active if delivery.split_exception)
        cards = [
            SummaryCard("Loading Now", str(loading_now), "Deliveries actively being loaded", "Live", "info"),
            SummaryCard("Signed CMR Pending", str(signed_pending), "Sent deliveries still awaiting signed CMR", "Pending", "warning"),
            SummaryCard("Split Exceptions", str(split_count), "Rare exception cases still kept secondary", "Rare", "neutral"),
        ]
        for card in cards:
            layout.addWidget(card)

        legend_panel = self._create_panel()
        legend_layout = QVBoxLayout(legend_panel)
        legend_layout.setContentsMargins(16, 16, 16, 16)
        legend_layout.setSpacing(10)

        legend_title = QLabel("Status Legend")
        legend_title.setObjectName("SectionTitle")
        legend_layout.addWidget(legend_title)

        for text, tone in [
            ("Released by transport", "success"),
            ("Documents pending", "warning"),
            ("Warehouse action needed", "info"),
            ("Loading in progress", "danger"),
        ]:
            row = QHBoxLayout()
            row.addWidget(StatusBadge(text, tone))
            row.addStretch(1)
            legend_layout.addLayout(row)

        layout.addWidget(legend_panel)
        layout.addStretch(1)
        return panel

    def _refresh_table(self) -> None:
        filtered_rows = self._filtered_rows()
        self._visible_rows = filtered_rows
        not_ready_rows = [row for row in filtered_rows if row.status_text != "Released By Transport"]
        released_rows = [row for row in filtered_rows if row.status_text == "Released By Transport"]
        self._not_ready_rows = not_ready_rows
        self._released_rows = released_rows
        self._populate_table(self.not_ready_table, not_ready_rows)
        self._populate_table(self.released_table, released_rows)
        self._refresh_summary_cards()

    def _populate_table(self, table: DataTable, rows: list[ShipmentOverviewRow]) -> None:
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            text_values = [
                row.delivery_slip_number,
                row.customer_name,
                row.destination_name,
                row.status_text + (" | Split" if row.is_split_exception else ""),
                str(row.pallet_count),
                f"{row.loading_progress_percent}%",
                row.warehouse_situation,
                row.document_readiness_text,
                row.signed_cmr_status_text,
            ]
            for column_index, value in enumerate(text_values):
                table.setItem(row_index, column_index, QTableWidgetItem(value))

            table.setCellWidget(row_index, 3, StatusBadge(row.status_text, row.status_tone))
            table.setCellWidget(row_index, 5, self._build_progress_widget(row.loading_progress_percent))
            table.setCellWidget(row_index, 6, StatusBadge(row.warehouse_situation, row.warehouse_tone))
            table.setCellWidget(
                row_index,
                7,
                StatusBadge(row.document_readiness_text, row.document_readiness_tone),
            )
            table.setCellWidget(
                row_index,
                8,
                StatusBadge(row.signed_cmr_status_text, row.signed_cmr_status_tone),
            )

            open_button = QPushButton("Open")
            open_button.setProperty("buttonRole", "primary")
            open_button.clicked.connect(
                lambda _checked=False, delivery_number=row.delivery_slip_number: self._open_delivery_by_number(delivery_number)
            )
            table.setCellWidget(row_index, 9, open_button)

        table.resizeRowsToContents()

    def _refresh_summary_cards(self) -> None:
        active_deliveries = self._workflow_store.active_deliveries()
        ready_count = sum(
            1 for delivery in active_deliveries if delivery.status == DeliverySlipStatus.RELEASED_BY_TRANSPORT
        )
        loading_count = sum(
            1 for delivery in active_deliveries if delivery.status == DeliverySlipStatus.LOADING_IN_PROGRESS
        )
        pending_attention = sum(1 for delivery in active_deliveries if not delivery.is_ready_for_release)
        self.open_deliveries_card.update_content(
            "Open Deliveries",
            str(len(active_deliveries)),
            "Daily working set focused on outbound deliveries still in process",
            "Operational",
            "info",
        )
        self.released_deliveries_card.update_content(
            "Released To Warehouse",
            str(ready_count),
            "Transport-ready deliveries visible for warehouse execution",
            "Ready",
            "success",
        )
        self.attention_needed_card.update_content(
            "Attention Needed",
            str(max(pending_attention, loading_count)),
            "Deliveries with missing documents or active loading work",
            "Watch",
            "warning",
        )

    def _filtered_rows(self) -> list[ShipmentOverviewRow]:
        rows = [self._to_row(delivery) for delivery in self._workflow_store.active_deliveries()]
        search_text = self.search_input.text().strip().lower()
        status_text = self.status_filter.currentText()
        readiness_text = self.readiness_filter.currentText()
        warehouse_text = self.warehouse_filter.currentText()

        filtered: list[ShipmentOverviewRow] = []
        for row in rows:
            if search_text and not self._matches_search(row, search_text):
                continue
            if status_text != "All statuses" and row.status_text != status_text:
                continue
            if readiness_text != "All readiness states" and row.document_readiness_text != readiness_text:
                continue
            if warehouse_text != "All warehouse states" and row.warehouse_situation != warehouse_text:
                continue
            filtered.append(row)

        sort_text = self.sort_filter.currentText()
        if sort_text == "Sort: Destination":
            filtered.sort(key=lambda row: row.destination_name.lower())
        elif sort_text == "Sort: Loading progress":
            filtered.sort(key=lambda row: row.loading_progress_percent, reverse=True)
        elif sort_text == "Sort: Pallet count":
            filtered.sort(key=lambda row: row.pallet_count, reverse=True)
        else:
            filtered.sort(key=lambda row: row.delivery_slip_number.lower())
        return filtered

    def _to_row(self, delivery: DeliveryWorkflowRecord) -> ShipmentOverviewRow:
        if delivery.status == DeliverySlipStatus.RELEASED_BY_TRANSPORT:
            status_tone = "success"
        elif delivery.status == DeliverySlipStatus.LOADING_IN_PROGRESS:
            status_tone = "danger"
        elif delivery.status == DeliverySlipStatus.DOCUMENTS_IN_PREPARATION:
            status_tone = "warning"
        else:
            status_tone = "info"

        staged_count = sum(1 for pallet in delivery.pallets if pallet.ready_to_load)
        if delivery.status == DeliverySlipStatus.LOADING_IN_PROGRESS:
            warehouse_text, warehouse_tone = "Loading Now", "danger"
        elif staged_count > 0:
            warehouse_text, warehouse_tone = "Staged", "info"
        else:
            warehouse_text, warehouse_tone = "Awaiting Action", "warning"

        readiness_tone = "success" if delivery.transport_readiness_text == "Ready" else "warning"
        signed_tone = {
            "Uploaded": "success",
            "Pending": "warning",
            "Expected Later": "info",
            "Not Applicable": "neutral",
        }[delivery.signed_cmr_status_text]

        return ShipmentOverviewRow(
            delivery_slip_number=delivery.delivery_slip_number,
            customer_name=delivery.customer_name,
            destination_name=delivery.destination_name,
            status_text=delivery.status.value.replace("_", " ").title(),
            status_tone=status_tone,
            pallet_count=delivery.total_pallets,
            loading_progress_percent=delivery.loading_progress_percent,
            warehouse_situation=warehouse_text,
            warehouse_tone=warehouse_tone,
            document_readiness_text=delivery.transport_readiness_text,
            document_readiness_tone=readiness_tone,
            signed_cmr_status_text=delivery.signed_cmr_status_text,
            signed_cmr_status_tone=signed_tone,
            is_split_exception=delivery.split_exception,
        )

    def _matches_search(self, row: ShipmentOverviewRow, search_text: str) -> bool:
        return any(
            search_text in value.lower()
            for value in [
                row.delivery_slip_number,
                row.customer_name,
                row.destination_name,
                row.warehouse_situation,
                row.document_readiness_text,
            ]
        )

    def _clear_filters(self) -> None:
        self.search_input.clear()
        self.status_filter.setCurrentIndex(0)
        self.readiness_filter.setCurrentIndex(0)
        self.warehouse_filter.setCurrentIndex(0)
        self.sort_filter.setCurrentIndex(0)

    def _open_selected_delivery(self) -> None:
        if self.released_table.currentRow() >= 0 and self.released_table.rowCount() > 0:
            self._open_released_delivery_from_row(self.released_table.item(self.released_table.currentRow(), 0))
            return
        if self.not_ready_table.currentRow() < 0 and self.not_ready_table.rowCount() > 0:
            self.not_ready_table.selectRow(0)
        if self.not_ready_table.currentRow() >= 0 and self.not_ready_table.rowCount() > 0:
            self._open_not_ready_delivery_from_row(self.not_ready_table.item(self.not_ready_table.currentRow(), 0))

    def _open_not_ready_delivery_from_row(self, item: QTableWidgetItem | None) -> None:
        if item is None:
            return
        row_index = item.row()
        if row_index < 0 or row_index >= len(getattr(self, "_not_ready_rows", [])):
            return
        delivery_number = self._not_ready_rows[row_index].delivery_slip_number
        self._open_delivery_by_number(delivery_number)

    def _open_released_delivery_from_row(self, item: QTableWidgetItem | None) -> None:
        if item is None:
            return
        row_index = item.row()
        if row_index < 0 or row_index >= len(getattr(self, "_released_rows", [])):
            return
        delivery_number = self._released_rows[row_index].delivery_slip_number
        self._open_delivery_by_number(delivery_number)

    def _open_delivery_by_number(self, delivery_number: str) -> None:
        self._workflow_store.set_current_delivery(delivery_number)
        self.open_in_warehouse_requested.emit(delivery_number)

    def _build_progress_widget(self, percent: int) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(percent)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat(f"{percent}%")
        layout.addWidget(progress_bar)
        return container

    def _create_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("ContentSurface")
        return panel

    def _caption(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionCaption")
        return label
