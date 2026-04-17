"""Transport screen for the desktop client."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from logistics_app.desktop.ui.widgets import (
    ActionToolbar,
    DataTable,
    DocumentCard,
    PageHeader,
    StatusBadge,
    SummaryCard,
)


@dataclass(frozen=True, slots=True)
class DocumentCardData:
    """Display data for a transport document card."""

    title: str
    filename: str
    metadata: str
    status_text: str
    status_tone: str


@dataclass(frozen=True, slots=True)
class PrintRequirementRow:
    """Display row for one print requirement."""

    document_type: str
    required_copies: str
    printed_copies: str
    remaining_copies: str
    default_printer: str
    readiness: str


class TransportScreenWindow(QMainWindow):
    """Transport workspace focused on document completeness and print setup."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Transport Workspace")
        self.resize(1480, 980)

        page_root = QWidget()
        page_root.setObjectName("PageRoot")

        content_layout = QVBoxLayout(page_root)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(18)

        page_header = PageHeader(
            title="Transport",
            subtitle=(
                "Source-of-truth workspace for delivery documents, print requirements, "
                "and readiness confirmation before warehouse loading."
            ),
        )
        self._build_header_actions(page_header)
        content_layout.addWidget(page_header)

        content_layout.addWidget(self._build_delivery_search_panel())
        content_layout.addWidget(self._build_action_toolbar())
        content_layout.addLayout(self._build_summary_cards())

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
        self.setCentralWidget(scroll_area)

    def _build_header_actions(self, page_header: PageHeader) -> None:
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_delivery)
        page_header.add_action_widget(refresh_button)

        open_queue_button = QPushButton("Open Queue")
        open_queue_button.clicked.connect(self._refresh_delivery)
        page_header.add_action_widget(open_queue_button)

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
        self.slip_input.setText("DEL-2026-0142")
        layout.addWidget(self.slip_input, 1, 1, 1, 2)

        layout.addWidget(self._caption("Customer"), 1, 3)
        self.customer_filter = QComboBox()
        self.customer_filter.addItems(["All customers", "Nordic Export BV", "Westport Logistics"])
        layout.addWidget(self.customer_filter, 1, 4)

        open_button = QPushButton("Open Delivery")
        open_button.setProperty("buttonRole", "primary")
        open_button.clicked.connect(self._refresh_delivery)
        layout.addWidget(open_button, 1, 5)

        recent_label = QLabel("Recent")
        recent_label.setObjectName("SectionCaption")
        layout.addWidget(recent_label, 2, 0)

        recent_row = QHBoxLayout()
        recent_row.setSpacing(8)
        for text in ["DEL-2026-0142", "DEL-2026-0143", "DEL-2026-0144"]:
            chip = QPushButton(text)
            chip.setProperty("buttonRole", "toolbar")
            chip.clicked.connect(lambda _checked=False, t=text: self._open_recent(t))
            recent_row.addWidget(chip)
        recent_row.addStretch(1)
        layout.addLayout(recent_row, 2, 1, 1, 5)
        return panel

    def _build_action_toolbar(self) -> ActionToolbar:
        toolbar = ActionToolbar("Transport Actions")
        toolbar.add_button("Upload Documents", role="primary").clicked.connect(self._refresh_delivery)
        toolbar.add_button("Adjust Print Copies").clicked.connect(self._refresh_delivery)
        toolbar.add_button("Confirm Readiness").clicked.connect(self._refresh_delivery)
        toolbar.add_button("Open Delivery History").clicked.connect(self._refresh_delivery)
        return toolbar

    def _build_summary_cards(self) -> QGridLayout:
        cards_layout = QGridLayout()
        cards_layout.setHorizontalSpacing(14)
        cards_layout.setVerticalSpacing(14)
        cards_layout.addWidget(
            SummaryCard(
                "Document Completeness",
                "5 / 6",
                "All core transport documents uploaded except signed CMR",
                "Pending",
                "warning",
            ),
            0,
            0,
        )
        cards_layout.addWidget(
            SummaryCard(
                "Print Copies Remaining",
                "4",
                "Warehouse still needs outbound print execution on 2 document types",
                "Operational",
                "info",
            ),
            0,
            1,
        )
        cards_layout.addWidget(
            SummaryCard(
                "Pallets Linked",
                "12",
                "All pallets currently associated with the main delivery slip",
                "Aligned",
                "success",
            ),
            0,
            2,
        )
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
            ("Delivery Slip", "DEL-2026-0142"),
            ("Transport Ref", "TRP-54821"),
            ("Customer", "Nordic Export BV"),
            ("Delivery Date", "2026-04-16"),
            ("Origin", "Moerdijk Warehouse"),
            ("Destination", "Rotterdam Terminal"),
            ("Status", "Documents Pending"),
            ("Print Mode", "Warehouse Execution"),
        ]
        for index, (label, value) in enumerate(fields):
            row = index // 2
            column = (index % 2) * 2
            grid.addWidget(self._caption(label), row, column)
            value_label = QLabel(value)
            value_label.setObjectName("MetaText")
            grid.addWidget(value_label, row, column + 1)
        layout.addLayout(grid)

        notes_label = QLabel("Transport Notes")
        notes_label.setObjectName("SectionCaption")
        layout.addWidget(notes_label)

        notes_box = QTextEdit()
        notes_box.setPlainText(
            "Customer requires certificate print with outbound pack. "
            "Signed CMR will be uploaded by warehouse after loading."
        )
        notes_box.setMinimumHeight(100)
        layout.addWidget(notes_box)
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
        top_row.addWidget(StatusBadge("Pending Warehouse Upload", "warning"))
        layout.addLayout(top_row)

        summary_label = QLabel(
            "Transport controls document completeness. Readiness should only be confirmed "
            "when all required transport-side documents are uploaded and print copies are defined."
        )
        summary_label.setObjectName("PageSubtitle")
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        checklist_group = QGroupBox("Readiness Checklist")
        checklist_layout = QVBoxLayout(checklist_group)
        checklist_layout.setContentsMargins(16, 16, 16, 16)
        checklist_layout.setSpacing(10)

        for text, checked in [
            ("Packing slip uploaded", True),
            ("CMR uploaded", True),
            ("Certificate uploaded", True),
            ("Print copies defined", True),
            ("Signed CMR expected after loading", True),
            ("Transport confirms release to warehouse", False),
        ]:
            checkbox = QCheckBox(text)
            checkbox.setChecked(checked)
            checklist_layout.addWidget(checkbox)
        layout.addWidget(checklist_group)

        confirm_button = QPushButton("Confirm Document Readiness")
        confirm_button.setProperty("buttonRole", "primary")
        confirm_button.clicked.connect(self._refresh_delivery)
        layout.addWidget(confirm_button, 0, Qt.AlignmentFlag.AlignRight)
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
        upload_button.clicked.connect(self._refresh_delivery)
        title_row.addWidget(upload_button)
        layout.addLayout(title_row)

        helper_text = QLabel(
            "Transport maintains the authoritative document set for this delivery. "
            "Signed CMR remains a separate document type and is expected later."
        )
        helper_text.setObjectName("PageSubtitle")
        helper_text.setWordWrap(True)
        layout.addWidget(helper_text)

        cards_layout = QGridLayout()
        cards_layout.setHorizontalSpacing(12)
        cards_layout.setVerticalSpacing(12)
        for index, card_data in enumerate(self._document_cards()):
            cards_layout.addWidget(
                DocumentCard(
                    title=card_data.title,
                    filename=card_data.filename,
                    metadata=card_data.metadata,
                    status_text=card_data.status_text,
                    status_tone=card_data.status_tone,
                ),
                index // 2,
                index % 2,
            )
        layout.addLayout(cards_layout)
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
        edit_button.clicked.connect(self._refresh_delivery)
        top_row.addWidget(edit_button)
        layout.addLayout(top_row)

        table = DataTable()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["Document Type", "Required", "Printed", "Remaining", "Default Printer", "Readiness"]
        )
        rows = self._print_requirement_rows()
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row.document_type,
                row.required_copies,
                row.printed_copies,
                row.remaining_copies,
                row.default_printer,
                row.readiness,
            ]
            for column_index, value in enumerate(values):
                table.setItem(row_index, column_index, QTableWidgetItem(value))
        layout.addWidget(table)
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
        top_row.addWidget(StatusBadge("12 Pallets Linked", "info"))
        layout.addLayout(top_row)

        helper_text = QLabel(
            "Transport can review pallet linkage here for confirmation. "
            "Warehouse remains responsible for physical location and movement handling."
        )
        helper_text.setObjectName("PageSubtitle")
        helper_text.setWordWrap(True)
        layout.addWidget(helper_text)

        table = DataTable()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(
            ["Pallet ID", "Status", "Location", "Packages", "Last Movement"]
        )
        rows = [
            ("PAL-0142-001", "In warehouse", "A-01-03", "8", "14:05"),
            ("PAL-0142-002", "In warehouse", "A-01-04", "10", "14:07"),
            ("PAL-0142-003", "Staged", "Dock 2", "6", "14:41"),
            ("PAL-0142-004", "Staged", "Dock 2", "4", "14:42"),
        ]
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                table.setItem(row_index, column_index, QTableWidgetItem(value))
        layout.addWidget(table)
        return panel

    def _build_split_transport_panel(self) -> QGroupBox:
        group_box = QGroupBox("Rare Split Transport Handling")
        group_box.setCheckable(True)
        group_box.setChecked(False)

        layout = QVBoxLayout(group_box)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        helper_text = QLabel(
            "Use this only when one main delivery slip must be divided operationally across multiple "
            "transport groups. The common workflow above remains unchanged."
        )
        helper_text.setObjectName("PageSubtitle")
        helper_text.setWordWrap(True)
        layout.addWidget(helper_text)

        split_table = DataTable()
        split_table.setColumnCount(4)
        split_table.setHorizontalHeaderLabels(
            ["Split Code", "Transport Ref", "Assigned Pallets", "Document Scope"]
        )
        split_rows = [
            ("A", "TRP-54821-A", "4", "CMR + stickers"),
            ("B", "TRP-54821-B", "8", "Packing slip + certificate"),
        ]
        split_table.setRowCount(len(split_rows))
        for row_index, row in enumerate(split_rows):
            for column_index, value in enumerate(row):
                split_table.setItem(row_index, column_index, QTableWidgetItem(value))
        layout.addWidget(split_table)

        actions_row = QHBoxLayout()
        actions_row.addStretch(1)

        add_split_button = QPushButton("Add Split Group")
        add_split_button.clicked.connect(self._refresh_delivery)
        actions_row.addWidget(add_split_button)

        review_split_button = QPushButton("Review Split Assignment")
        review_split_button.clicked.connect(self._refresh_delivery)
        actions_row.addWidget(review_split_button)

        layout.addLayout(actions_row)
        return group_box

    def _refresh_delivery(self) -> None:
        """Demo placeholder for delivery state refresh."""
        pass

    def _open_recent(self, slip_number: str) -> None:
        """Demo placeholder for opening a recent delivery."""
        self.slip_input.setText(slip_number)
        self._refresh_delivery()

    def _document_cards(self) -> list[DocumentCardData]:
        return [
            DocumentCardData(
                title="Packing Slip",
                filename="PackingSlip_DEL-2026-0142.pdf",
                metadata="Version 1 | Uploaded by transport.office | 13:10",
                status_text="Available",
                status_tone="success",
            ),
            DocumentCardData(
                title="CMR",
                filename="CMR_DEL-2026-0142.pdf",
                metadata="Version 2 | Uploaded by transport.office | 14:22",
                status_text="Available",
                status_tone="success",
            ),
            DocumentCardData(
                title="Certificate",
                filename="Certificate_Export_0142.pdf",
                metadata="Version 1 | Office print route defined",
                status_text="Available",
                status_tone="success",
            ),
            DocumentCardData(
                title="Transport Document",
                filename="TransportDoc_0142.pdf",
                metadata="Version 1 | Awaiting warehouse print execution",
                status_text="Ready",
                status_tone="info",
            ),
            DocumentCardData(
                title="Sticker",
                filename="Sticker_0142.zpl",
                metadata="Label print requirement confirmed | Dock printer route",
                status_text="Ready",
                status_tone="info",
            ),
            DocumentCardData(
                title="Signed CMR",
                filename="Not uploaded yet",
                metadata="Expected from warehouse after loading | Stored separately from original CMR",
                status_text="Pending",
                status_tone="warning",
            ),
        ]

    def _print_requirement_rows(self) -> list[PrintRequirementRow]:
        return [
            PrintRequirementRow("Packing Slip", "2", "0", "2", "Warehouse_Main_01", "Configured"),
            PrintRequirementRow("CMR", "2", "0", "2", "Warehouse_Main_01", "Configured"),
            PrintRequirementRow("Certificate", "1", "0", "1", "Office_01", "Configured"),
            PrintRequirementRow("Sticker", "1", "0", "1", "Label_01", "Configured"),
            PrintRequirementRow("Signed CMR", "0", "0", "0", "Office_01", "Awaiting upload"),
        ]

    def _create_panel(self, object_name: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName(object_name)
        return panel

    def _caption(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionCaption")
        return label
