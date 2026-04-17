"""Warehouse screen for the desktop client."""

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
class WarehouseDocumentCardData:
    """Display data for warehouse document access cards."""

    title: str
    filename: str
    metadata: str
    status_text: str
    status_tone: str


@dataclass(frozen=True, slots=True)
class WarehousePrintRow:
    """Display row for warehouse print execution tracking."""

    document_type: str
    required_copies: str
    printed_copies: str
    remaining_copies: str
    printer_name: str
    action_state: str


class WarehouseScreenWindow(QMainWindow):
    """Warehouse workspace optimized for scan speed, pallet handling, and print execution."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Warehouse Workspace")
        self.resize(1520, 980)

        page_root = QWidget()
        page_root.setObjectName("PageRoot")

        content_layout = QVBoxLayout(page_root)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(18)

        page_header = PageHeader(
            title="Warehouse",
            subtitle=(
                "Fast workstation flow for pallet handling, loading, document access, "
                "and outbound print execution driven by transport readiness."
            ),
        )
        self._build_header_actions(page_header)
        content_layout.addWidget(page_header)

        content_layout.addWidget(self._build_scan_panel())
        content_layout.addWidget(self._build_action_toolbar())
        content_layout.addLayout(self._build_summary_cards())

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

    def _build_header_actions(self, page_header: PageHeader) -> None:
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_all)
        page_header.add_action_widget(refresh_button)

        create_button = QPushButton("Create Delivery Note")
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

        helper_label = QLabel(
            "Use pallet ID for the fastest operational flow, or open the main delivery slip when handling a full load."
        )
        helper_label.setObjectName("PageSubtitle")
        helper_label.setWordWrap(True)
        layout.addWidget(helper_label, 1, 0, 1, 6)

        layout.addWidget(self._caption("Scan Input"), 2, 0)
        self.scan_input = QLineEdit()
        self.scan_input.setPlaceholderText("Scan pallet ID or enter main delivery slip number")
        self.scan_input.setText("PAL-0142-003")
        self.scan_input.setMinimumHeight(52)
        self.scan_input.setStyleSheet("font-size: 16pt; font-weight: 600;")
        layout.addWidget(self.scan_input, 2, 1, 1, 3)

        open_button = QPushButton("Open")
        open_button.setProperty("buttonRole", "primary")
        open_button.setMinimumHeight(52)
        open_button.clicked.connect(self._refresh_all)
        layout.addWidget(open_button, 2, 4)

        clear_button = QPushButton("Clear")
        clear_button.setMinimumHeight(52)
        clear_button.clicked.connect(self.scan_input.clear)
        layout.addWidget(clear_button, 2, 5)
        return panel

    def _build_action_toolbar(self) -> ActionToolbar:
        toolbar = ActionToolbar("Warehouse Actions")
        toolbar.add_button("Create Delivery Note", role="primary").clicked.connect(self._create_delivery)
        toolbar.add_button("Assign Location").clicked.connect(self._refresh_all)
        toolbar.add_button("Move Pallet").clicked.connect(self._refresh_all)
        toolbar.add_button("Mark Loaded").clicked.connect(self._refresh_all)
        toolbar.add_button("Print Remaining").clicked.connect(self._refresh_all)
        toolbar.add_button("Upload Signed CMR").clicked.connect(self._refresh_all)
        return toolbar

    def _build_summary_cards(self) -> QGridLayout:
        cards_layout = QGridLayout()
        cards_layout.setHorizontalSpacing(14)
        cards_layout.setVerticalSpacing(14)
        cards_layout.addWidget(
            SummaryCard(
                "Current Delivery",
                "DEL-2026-0142",
                "Transport has released the delivery to warehouse execution",
                "Ready",
                "success",
            ),
            0,
            0,
        )
        cards_layout.addWidget(
            SummaryCard(
                "Pallets Staged",
                "4 / 12",
                "Four pallets are already moved to loading dock positions",
                "Operational",
                "info",
            ),
            0,
            1,
        )
        cards_layout.addWidget(
            SummaryCard(
                "Print Copies Remaining",
                "4",
                "Warehouse still needs to print packing slip and CMR copies",
                "Action",
                "warning",
            ),
            0,
            2,
        )
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
        top_row.addWidget(StatusBadge("Released To Warehouse", "success"))
        layout.addLayout(top_row)

        helper_label = QLabel(
            "Warehouse follows transport's readiness state. Document completeness is not decided here."
        )
        helper_label.setObjectName("PageSubtitle")
        helper_label.setWordWrap(True)
        layout.addWidget(helper_label)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        rows = [
            ("Delivery Slip", "DEL-2026-0142"),
            ("Transport Status", "Document readiness confirmed"),
            ("Customer", "Nordic Export BV"),
            ("Destination", "Rotterdam Terminal"),
            ("Required Docs", "Packing slip, CMR, certificate, sticker"),
            ("Signed CMR", "Expected after warehouse loading"),
        ]
        for index, (label, value) in enumerate(rows):
            grid.addWidget(self._caption(label), index, 0)
            value_label = QLabel(value)
            value_label.setObjectName("MetaText")
            value_label.setWordWrap(True)
            grid.addWidget(value_label, index, 1)
        layout.addLayout(grid)
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

        helper_label = QLabel(
            "Upload signed CMR only after loading when applicable. It remains a separate document type and never replaces the original CMR."
        )
        helper_label.setObjectName("PageSubtitle")
        helper_label.setWordWrap(True)
        layout.addWidget(helper_label)

        upload_notes = QTextEdit()
        upload_notes.setPlainText(
            "Loading complete. Await signed paperwork from dock team before upload."
        )
        upload_notes.setMinimumHeight(110)
        layout.addWidget(upload_notes)

        actions_row = QHBoxLayout()
        upload_button = QPushButton("Upload Signed CMR")
        upload_button.setProperty("buttonRole", "primary")
        upload_button.clicked.connect(self._refresh_all)
        actions_row.addWidget(upload_button)

        open_signed_button = QPushButton("Open Existing Signed CMR")
        open_signed_button.clicked.connect(self._refresh_all)
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
        top_row.addWidget(StatusBadge("12 Linked", "info"))
        layout.addLayout(top_row)

        table = DataTable()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["Pallet ID", "Status", "Current Location", "Packages", "Ready To Load", "Last Movement"]
        )
        rows = [
            ("PAL-0142-001", "In warehouse", "A-01-03", "8", "No", "14:05"),
            ("PAL-0142-002", "In warehouse", "A-01-04", "10", "No", "14:07"),
            ("PAL-0142-003", "Staged", "Dock 2", "6", "Yes", "14:41"),
            ("PAL-0142-004", "Loaded", "Truck Lane 3", "4", "Done", "14:52"),
            ("PAL-0142-005", "Staged", "Dock 2", "7", "Yes", "14:46"),
        ]
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                table.setItem(row_index, column_index, QTableWidgetItem(value))
        layout.addWidget(table)
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

        pallet_input = QLineEdit()
        pallet_input.setText("PAL-0142-003")
        location_input = QLineEdit()
        location_input.setPlaceholderText("A-01-03 or Dock 2")
        location_input.setText("Dock 2")
        move_reason = QComboBox()
        move_reason.addItems(["Stage for loading", "Relocate", "Correct location", "Load to truck"])

        form_grid.addWidget(self._caption("Selected Pallet"), 0, 0)
        form_grid.addWidget(pallet_input, 0, 1)
        form_grid.addWidget(self._caption("Target Location"), 1, 0)
        form_grid.addWidget(location_input, 1, 1)
        form_grid.addWidget(self._caption("Action"), 2, 0)
        form_grid.addWidget(move_reason, 2, 1)
        layout.addLayout(form_grid)

        action_buttons = QVBoxLayout()
        assign_button = QPushButton("Assign Warehouse Location")
        assign_button.setProperty("buttonRole", "primary")
        move_button = QPushButton("Move Pallet")
        load_button = QPushButton("Mark Pallet As Loaded")
        finalize_button = QPushButton("Finalize Shipment (Ship)")
        finalize_button.setProperty("buttonRole", "primary")

        for button in [assign_button, move_button, load_button, finalize_button]:
            button.setMinimumHeight(40)
            if button == finalize_button:
                button.clicked.connect(self._on_finalize_shipment)
            else:
                button.clicked.connect(self._refresh_all)
            action_buttons.addWidget(button)

        action_buttons.addStretch(1)
        layout.addLayout(action_buttons)
        return panel

    def _build_documents_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title_row = QHBoxLayout()
        title_label = QLabel("Quick Document Access")
        title_label.setObjectName("SectionTitle")
        title_row.addWidget(title_label)
        title_row.addStretch(1)

        open_all_button = QPushButton("Open All Documents")
        open_all_button.clicked.connect(self._refresh_all)
        title_row.addWidget(open_all_button)
        layout.addLayout(title_row)

        helper_label = QLabel(
            "Warehouse can quickly open and print the documents transport has already made ready."
        )
        helper_label.setObjectName("PageSubtitle")
        helper_label.setWordWrap(True)
        layout.addWidget(helper_label)

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

    def _build_print_execution_panel(self) -> QFrame:
        panel = self._create_panel("ContentSurface")
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
        print_all_button.clicked.connect(self._refresh_all)
        top_row.addWidget(print_all_button)
        layout.addLayout(top_row)

        helper_label = QLabel(
            "Warehouse executes printing against transport-defined requirements. Manual workstation printer override remains available when needed."
        )
        helper_label.setObjectName("PageSubtitle")
        helper_label.setWordWrap(True)
        layout.addWidget(helper_label)

        table = DataTable()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["Document Type", "Required", "Printed", "Remaining", "Printer", "Action State"]
        )
        rows = self._print_rows()
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row.document_type,
                row.required_copies,
                row.printed_copies,
                row.remaining_copies,
                row.printer_name,
                row.action_state,
            ]
            for column_index, value in enumerate(values):
                table.setItem(row_index, column_index, QTableWidgetItem(value))
        layout.addWidget(table)

        action_row = QHBoxLayout()
        print_selected_button = QPushButton("Print Selected")
        print_selected_button.clicked.connect(self._refresh_all)
        action_row.addWidget(print_selected_button)

        manual_override_button = QPushButton("Manual Printer Override")
        manual_override_button.clicked.connect(self._refresh_all)
        action_row.addWidget(manual_override_button)

        reprint_button = QPushButton("Reprint Last Job")
        reprint_button.clicked.connect(self._refresh_all)
        action_row.addWidget(reprint_button)

        action_row.addStretch(1)
        layout.addLayout(action_row)
        return panel

    def _refresh_all(self) -> None:
        """Demo placeholder for operational actions."""
        # In a real app, this would refresh data from the API.
        pass

    def _create_delivery(self) -> None:
        """Demo placeholder for generating a new delivery note in the warehouse."""
        pass

    def _on_finalize_shipment(self) -> None:
        """Demo placeholder for loading completeness check and shipment finalization."""
        # Simulated completeness check
        total = 12
        loaded = 12 # Change to 11 to simulate error

        if loaded < total:
            from logistics_app.desktop.ui.dialogs import BaseDialog
            dialog = BaseDialog(
                title="Loading Incomplete",
                message=f"Cannot finalize shipment. {total - loaded} pallets are still not loaded.",
                parent=self
            )
            dialog.add_action_button("OK", role="primary").clicked.connect(dialog.accept)
            dialog.exec()
        else:
            from logistics_app.desktop.ui.dialogs import BaseDialog
            dialog = BaseDialog(
                title="Shipment Finalized",
                message="All pallets loaded. Status changed to SHIPPED. Delivery note will move to Sent history.",
                parent=self
            )
            dialog.add_action_button("OK", role="primary").clicked.connect(dialog.accept)
            dialog.exec()
            self._refresh_all()

    def _document_cards(self) -> list[WarehouseDocumentCardData]:
        return [
            WarehouseDocumentCardData(
                title="Packing Slip",
                filename="PackingSlip_DEL-2026-0142.pdf",
                metadata="Ready from transport | Open or print immediately",
                status_text="Ready",
                status_tone="success",
            ),
            WarehouseDocumentCardData(
                title="CMR",
                filename="CMR_DEL-2026-0142.pdf",
                metadata="Original transport CMR | Signed version is separate",
                status_text="Ready",
                status_tone="success",
            ),
            WarehouseDocumentCardData(
                title="Certificate",
                filename="Certificate_Export_0142.pdf",
                metadata="Required for outbound pack | Office printer route",
                status_text="Ready",
                status_tone="info",
            ),
            WarehouseDocumentCardData(
                title="Signed CMR",
                filename="Not uploaded yet",
                metadata="Upload only after loading when signed copy exists",
                status_text="Pending",
                status_tone="warning",
            ),
        ]

    def _print_rows(self) -> list[WarehousePrintRow]:
        return [
            WarehousePrintRow("Packing Slip", "2", "0", "2", "Warehouse_Main_01", "Print now"),
            WarehousePrintRow("CMR", "2", "0", "2", "Warehouse_Main_01", "Print now"),
            WarehousePrintRow("Certificate", "1", "1", "0", "Office_01", "Done"),
            WarehousePrintRow("Sticker", "1", "1", "0", "Label_01", "Done"),
            WarehousePrintRow("Signed CMR", "0", "0", "0", "Office_01", "Await upload"),
        ]

    def _create_panel(self, object_name: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName(object_name)
        return panel

    def _caption(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionCaption")
        return label
