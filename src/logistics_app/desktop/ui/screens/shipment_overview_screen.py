"""Shipment overview screen for open delivery monitoring."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
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

from logistics_app.desktop.ui.dialogs import BaseDialog
from logistics_app.desktop.ui.widgets import ActionToolbar, DataTable, PageHeader, StatusBadge, SummaryCard


@dataclass(frozen=True, slots=True)
class ShipmentOverviewRow:
    """Display model for one open delivery row."""

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
    is_split_exception: bool = False


class DeliverySlipQuickViewDialog(BaseDialog):
    """Compact dialog for fast delivery review from the overview screen."""

    def __init__(self, row: ShipmentOverviewRow, parent: QWidget | None = None) -> None:
        super().__init__(
            title=f"Delivery {row.delivery_slip_number}",
            message=(
                "Quick operational view for handoff into transport or warehouse actions. "
                "This keeps the overview screen fast while still allowing a one-click detail check."
            ),
            parent=parent,
        )
        self.resize(560, 360)

        details_grid = QGridLayout()
        details_grid.setHorizontalSpacing(16)
        details_grid.setVerticalSpacing(10)

        detail_rows = [
            ("Customer", row.customer_name),
            ("Destination", row.destination_name),
            ("Status", row.status_text),
            ("Pallets", str(row.pallet_count)),
            ("Loading Progress", f"{row.loading_progress_percent}%"),
            ("Warehouse", row.warehouse_situation),
            ("Transport Readiness", row.document_readiness_text),
            ("Signed CMR", row.signed_cmr_status_text),
            ("Split Transport", "Exception case" if row.is_split_exception else "Standard flow"),
        ]
        for row_index, (label_text, value_text) in enumerate(detail_rows):
            details_grid.addWidget(self._caption(label_text), row_index, 0)
            details_grid.addWidget(self._value(value_text), row_index, 1)

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
    """Operational overview of open delivery slips."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Shipment Overview")
        self.resize(1500, 980)

        self._rows = self._build_demo_rows()
        self._visible_rows: list[ShipmentOverviewRow] = []

        page_root = QWidget()
        page_root.setObjectName("PageRoot")

        content_layout = QVBoxLayout(page_root)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(18)

        page_header = PageHeader(
            title="Shipment Overview",
            subtitle=(
                "Operational overview of open delivery slips, loading progress, "
                "warehouse state, and transport readiness."
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

        title_label = QLabel("Filter Open Deliveries")
        title_label.setObjectName("SectionTitle")
        layout.addWidget(title_label, 0, 0, 1, 8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search delivery slip, customer, destination, or pallet reference")
        self.search_input.textChanged.connect(self._refresh_table)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All statuses", "Ready to load", "Documents pending", "In warehouse", "Loaded"])
        self.status_filter.currentIndexChanged.connect(self._refresh_table)

        self.readiness_filter = QComboBox()
        self.readiness_filter.addItems(["All readiness states", "Ready", "Pending", "Blocked"])
        self.readiness_filter.currentIndexChanged.connect(self._refresh_table)

        self.warehouse_filter = QComboBox()
        self.warehouse_filter.addItems(["All warehouse states", "Staged", "Awaiting action", "Loading now"])
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
        open_button = toolbar.add_button("Open Selected Delivery", role="primary")
        open_button.clicked.connect(self._open_selected_delivery)

        details_button = toolbar.add_button("Quick Delivery View")
        details_button.clicked.connect(self._open_selected_delivery)

        clear_filters_button = toolbar.add_button("Clear Filters")
        clear_filters_button.clicked.connect(self._clear_filters)

        refresh_button = toolbar.add_button("Refresh Queue")
        refresh_button.clicked.connect(self._refresh_table)
        return toolbar

    def _build_summary_cards(self) -> QGridLayout:
        cards_layout = QGridLayout()
        cards_layout.setHorizontalSpacing(14)
        cards_layout.setVerticalSpacing(14)
        cards_layout.addWidget(
            SummaryCard(
                "Open Deliveries",
                "18",
                "Daily working set focused on the normal outbound flow",
                "Operational",
                "info",
            ),
            0,
            0,
        )
        cards_layout.addWidget(
            SummaryCard(
                "Ready To Load",
                "9",
                "Transport-ready deliveries with clear document readiness",
                "Good",
                "success",
            ),
            0,
            1,
        )
        cards_layout.addWidget(
            SummaryCard(
                "Warehouse Attention",
                "4",
                "Deliveries awaiting pallet action, print work, or signed CMR follow-up",
                "Watch",
                "warning",
            ),
            0,
            2,
        )
        return cards_layout

    def _build_open_deliveries_panel(self) -> QFrame:
        panel = self._create_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title_row = QHBoxLayout()
        title_label = QLabel("Open Delivery Slips")
        title_label.setObjectName("SectionTitle")
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        title_row.addWidget(StatusBadge("Common Flow First", "info"))
        layout.addLayout(title_row)

        helper_text = QLabel(
            "The default view focuses on standard delivery execution. Rare split transport cases are "
            "visible only as a small exception marker and do not change the overall layout."
        )
        helper_text.setObjectName("PageSubtitle")
        helper_text.setWordWrap(True)
        layout.addWidget(helper_text)

        self.deliveries_table = DataTable()
        self.deliveries_table.setColumnCount(10)
        self.deliveries_table.setHorizontalHeaderLabels(
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
        self.deliveries_table.setSortingEnabled(False)
        self.deliveries_table.itemDoubleClicked.connect(self._open_delivery_from_row)
        layout.addWidget(self.deliveries_table)
        return panel

    def _build_queue_context_panel(self) -> QFrame:
        panel = self._create_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        section_title = QLabel("Operational Situation")
        section_title.setObjectName("SectionTitle")
        layout.addWidget(section_title)

        cards = [
            SummaryCard("Loading Now", "3", "Deliveries actively being staged or loaded", "Live", "info"),
            SummaryCard("Signed CMR Pending", "5", "Post-loading signed paperwork still expected", "Pending", "warning"),
            SummaryCard("Split Exceptions", "1", "Small number of exceptional split transport cases", "Rare", "neutral"),
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
            ("Ready to load", "success"),
            ("Documents pending", "warning"),
            ("Warehouse action needed", "info"),
            ("Operational issue", "danger"),
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
        self.deliveries_table.setRowCount(len(filtered_rows))
        self._visible_rows = filtered_rows
        for row_index, row in enumerate(filtered_rows):
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
                item = QTableWidgetItem(value)
                if column_index == 4:
                    item.setData(Qt.ItemDataRole.UserRole, row.pallet_count)
                if column_index == 5:
                    item.setData(Qt.ItemDataRole.UserRole, row.loading_progress_percent)
                self.deliveries_table.setItem(row_index, column_index, item)

            self.deliveries_table.setCellWidget(row_index, 3, StatusBadge(row.status_text, row.status_tone))
            self.deliveries_table.setCellWidget(
                row_index,
                5,
                self._build_progress_widget(row.loading_progress_percent),
            )
            self.deliveries_table.setCellWidget(
                row_index,
                6,
                StatusBadge(row.warehouse_situation, row.warehouse_tone),
            )
            self.deliveries_table.setCellWidget(
                row_index,
                7,
                StatusBadge(row.document_readiness_text, row.document_readiness_tone),
            )
            self.deliveries_table.setCellWidget(
                row_index,
                8,
                StatusBadge(row.signed_cmr_status_text, row.signed_cmr_status_tone),
            )

            open_button = QPushButton("Open")
            open_button.setProperty("buttonRole", "primary")
            open_button.clicked.connect(lambda _checked=False, index=row_index: self._open_delivery_by_index(index))
            self.deliveries_table.setCellWidget(row_index, 9, open_button)

        self.deliveries_table.resizeRowsToContents()

    def _open_selected_delivery(self) -> None:
        current_row = self.deliveries_table.currentRow()
        if current_row < 0 and self.deliveries_table.rowCount() > 0:
            current_row = 0
            self.deliveries_table.selectRow(0)
        if current_row >= 0:
            self._open_delivery_by_index(current_row)

    def _open_delivery_from_row(self, item: QTableWidgetItem) -> None:
        self._open_delivery_by_index(item.row())

    def _open_delivery_by_index(self, row_index: int) -> None:
        if row_index < 0 or row_index >= len(self._visible_rows):
            return
        dialog = DeliverySlipQuickViewDialog(self._visible_rows[row_index], parent=self)
        dialog.exec()

    def _filtered_rows(self) -> list[ShipmentOverviewRow]:
        search_text = self.search_input.text().strip().lower()
        status_text = self.status_filter.currentText()
        readiness_text = self.readiness_filter.currentText()
        warehouse_text = self.warehouse_filter.currentText()

        rows = []
        for row in self._rows:
            if search_text and not self._matches_search(row, search_text):
                continue
            if status_text != "All statuses" and row.status_text != status_text:
                continue
            if readiness_text != "All readiness states" and row.document_readiness_text != readiness_text:
                continue
            if warehouse_text != "All warehouse states" and row.warehouse_situation != warehouse_text:
                continue
            rows.append(row)

        sort_text = self.sort_filter.currentText()
        if sort_text == "Sort: Destination":
            rows.sort(key=lambda row: row.destination_name.lower())
        elif sort_text == "Sort: Loading progress":
            rows.sort(key=lambda row: row.loading_progress_percent, reverse=True)
        elif sort_text == "Sort: Pallet count":
            rows.sort(key=lambda row: row.pallet_count, reverse=True)
        else:
            rows.sort(key=lambda row: row.delivery_slip_number.lower())
        return rows

    def _matches_search(self, row: ShipmentOverviewRow, search_text: str) -> bool:
        searchable_values = [
            row.delivery_slip_number,
            row.customer_name,
            row.destination_name,
            row.warehouse_situation,
            row.document_readiness_text,
        ]
        return any(search_text in value.lower() for value in searchable_values)

    def _clear_filters(self) -> None:
        self.search_input.clear()
        self.status_filter.setCurrentIndex(0)
        self.readiness_filter.setCurrentIndex(0)
        self.warehouse_filter.setCurrentIndex(0)
        self.sort_filter.setCurrentIndex(0)

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

    def _build_demo_rows(self) -> list[ShipmentOverviewRow]:
        return [
            ShipmentOverviewRow(
                "DEL-2026-0142",
                "Nordic Export BV",
                "Rotterdam Terminal",
                "Ready to load",
                "success",
                12,
                72,
                "Staged",
                "info",
                "Ready",
                "success",
                "Pending",
                "warning",
            ),
            ShipmentOverviewRow(
                "DEL-2026-0143",
                "Westport Logistics",
                "Antwerp",
                "Documents pending",
                "warning",
                8,
                25,
                "Awaiting action",
                "warning",
                "Pending",
                "warning",
                "Not applicable",
                "neutral",
            ),
            ShipmentOverviewRow(
                "DEL-2026-0144",
                "Nordic Export BV",
                "Hamburg",
                "Loaded",
                "info",
                16,
                100,
                "Loading now",
                "success",
                "Ready",
                "success",
                "Uploaded",
                "success",
            ),
            ShipmentOverviewRow(
                "DEL-2026-0145",
                "Harbor Export Group",
                "Lille",
                "In warehouse",
                "info",
                4,
                40,
                "Awaiting action",
                "warning",
                "Ready",
                "success",
                "Pending",
                "warning",
            ),
            ShipmentOverviewRow(
                "DEL-2026-0146",
                "Delta Cargo",
                "Le Havre",
                "Ready to load",
                "success",
                10,
                60,
                "Staged",
                "info",
                "Ready",
                "success",
                "Pending",
                "warning",
                is_split_exception=True,
            ),
        ]

    def _create_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("ContentSurface")
        return panel

    def _caption(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionCaption")
        return label
