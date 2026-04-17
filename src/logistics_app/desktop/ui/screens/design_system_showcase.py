"""Showcase window for the reusable desktop design system."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QScrollArea,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from logistics_app.desktop.ui.widgets import (
    ActionToolbar,
    DataTable,
    DocumentCard,
    FilterBar,
    PageHeader,
    StatusBadge,
    SummaryCard,
)


class DesignSystemShowcaseWindow(QMainWindow):
    """Internal preview window for the desktop design system."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Internal Logistics Design System")
        self.resize(1400, 920)

        page_root = QWidget()
        page_root.setObjectName("PageRoot")

        content_layout = QVBoxLayout(page_root)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(18)

        page_header = PageHeader(
            title="Outbound Logistics Dashboard",
            subtitle=(
                "Shared desktop design system for transport and warehouse operations. "
                "Built for fast, clear execution under operational pressure."
            ),
        )
        content_layout.addWidget(page_header)

        action_toolbar = ActionToolbar("Daily Actions")
        action_toolbar.add_button("Create Delivery", role="primary")
        action_toolbar.add_button("Print Documents")
        action_toolbar.add_button("Upload Signed CMR")
        action_toolbar.add_button("Refresh Queue")
        content_layout.addWidget(action_toolbar)

        filter_bar = FilterBar()
        filter_bar.status_filter.addItems(["Ready to load", "In warehouse", "Loaded", "Exception"])
        filter_bar.type_filter.addItems(["Delivery slips", "Pallets", "Documents", "Print jobs"])
        content_layout.addWidget(filter_bar)

        cards_layout = QGridLayout()
        cards_layout.setHorizontalSpacing(14)
        cards_layout.setVerticalSpacing(14)
        cards_layout.addWidget(
            SummaryCard("Deliveries Ready", "18", "Awaiting document print and final load confirmation", "Stable", "success"),
            0,
            0,
        )
        cards_layout.addWidget(
            SummaryCard("Pallet Exceptions", "3", "Require location or document correction before release", "Attention", "warning"),
            0,
            1,
        )
        cards_layout.addWidget(
            SummaryCard("Print Queue", "7", "Warehouse workstations currently processing outbound jobs", "Active", "info"),
            0,
            2,
        )
        content_layout.addLayout(cards_layout)

        document_section = QWidget()
        document_layout = QVBoxLayout(document_section)
        document_layout.setContentsMargins(0, 0, 0, 0)
        document_layout.setSpacing(12)

        section_title = QLabel("Documents Requiring Attention")
        section_title.setObjectName("SectionTitle")
        document_layout.addWidget(section_title)

        document_cards_row = QHBoxLayout()
        document_cards_row.setSpacing(14)
        document_cards_row.addWidget(
            DocumentCard(
                title="CMR",
                filename="CMR_DEL-2026-0142.pdf",
                metadata="Version 2 • Uploaded by transport.office • 14:22",
                status_text="Available",
                status_tone="success",
            )
        )
        document_cards_row.addWidget(
            DocumentCard(
                title="Signed CMR",
                filename="Awaiting upload after loading",
                metadata="Expected for outbound delivery DEL-2026-0142",
                status_text="Pending",
                status_tone="warning",
            )
        )
        document_cards_row.addWidget(
            DocumentCard(
                title="Certificate",
                filename="Cert_Export_0142.pdf",
                metadata="Required for destination compliance • Office printer route",
                status_text="Review",
                status_tone="info",
            )
        )
        document_layout.addLayout(document_cards_row)
        content_layout.addWidget(document_section)

        table_title = QLabel("Operational Queue")
        table_title.setObjectName("SectionTitle")
        content_layout.addWidget(table_title)

        queue_table = DataTable()
        queue_table.setColumnCount(6)
        queue_table.setHorizontalHeaderLabels(
            ["Delivery Slip", "Destination", "Status", "Pallets", "Documents", "Last Update"]
        )
        queue_table.setRowCount(4)
        rows = [
            ("DEL-2026-0142", "Rotterdam", "Ready to load", "12", "5/6", "15:04"),
            ("DEL-2026-0143", "Antwerp", "Documents pending", "8", "3/5", "14:58"),
            ("DEL-2026-0144", "Hamburg", "Loaded", "16", "6/6", "14:41"),
            ("DEL-2026-0145", "Lille", "Pallet exception", "4", "2/4", "14:33"),
        ]
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                queue_table.setItem(row_index, column_index, QTableWidgetItem(value))
        content_layout.addWidget(queue_table, 1)

        badge_row = QHBoxLayout()
        badge_row.setSpacing(8)
        badge_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        badge_row.addWidget(StatusBadge("Ready", "success"))
        badge_row.addWidget(StatusBadge("Pending", "warning"))
        badge_row.addWidget(StatusBadge("Issue", "danger"))
        badge_row.addWidget(StatusBadge("Info", "info"))
        content_layout.addLayout(badge_row)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(page_root)
        self.setCentralWidget(scroll_area)
