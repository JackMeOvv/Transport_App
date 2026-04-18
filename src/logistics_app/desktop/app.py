"""Desktop application entry point."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from logistics_app.desktop.ui.screens import (
    ShipmentOverviewScreenWindow,
    TransportScreenWindow,
    WarehouseScreenWindow,
)
from logistics_app.desktop.workflow import get_workflow_store
from logistics_app.desktop.ui.theme import apply_enterprise_light_theme


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Logistics App")
        self.resize(1400, 900)

        self._current_role = "Admin"
        self._programmatic_switch = False
        self._workflow_store = get_workflow_store()

        self.tabs = QTabWidget()
        self.shipment_overview_screen = ShipmentOverviewScreenWindow()
        self.warehouse_screen = WarehouseScreenWindow()
        self.transport_screen = TransportScreenWindow()

        self.tabs.addTab(self.shipment_overview_screen, "Shipment Overview")
        self.tabs.addTab(self.warehouse_screen, "Warehouse")
        self.tabs.addTab(self.transport_screen, "Transport")

        self.shipment_overview_screen.open_in_warehouse_requested.connect(self._open_in_warehouse)
        self.tabs.currentChanged.connect(self._handle_tab_change)

        root_container = QWidget()
        root_layout = QVBoxLayout(root_container)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        role_bar = QHBoxLayout()
        role_bar.setContentsMargins(12, 8, 12, 8)
        role_bar.addStretch(1)
        role_bar.addWidget(QLabel("Active Role:"))
        self.role_selector = QComboBox()
        self.role_selector.addItems(["Admin", "Transport", "Warehouse"])
        self.role_selector.currentTextChanged.connect(self._handle_role_change)
        role_bar.addWidget(self.role_selector)
        root_layout.addLayout(role_bar)
        root_layout.addWidget(self.tabs)

        self.setCentralWidget(root_container)
        self._handle_role_change(self._current_role)

    def _open_in_warehouse(self, _delivery_slip_number: str) -> None:
        """Switch the shell to the warehouse workspace for the selected delivery."""
        self._programmatic_switch = True
        self.tabs.setCurrentWidget(self.warehouse_screen)
        self._programmatic_switch = False

    def _handle_role_change(self, role: str) -> None:
        """Filter tab visibility and functionality based on user role."""
        self._current_role = role
        self.tabs.setTabVisible(0, role in {"Admin"})  # Overview
        self.tabs.setTabVisible(1, role in {"Admin", "Warehouse"})  # Warehouse
        self.tabs.setTabVisible(2, role in {"Admin", "Transport"})  # Transport

        # Ensure the selected tab is actually visible
        if not self.tabs.isTabVisible(self.tabs.currentIndex()):
            for i in range(self.tabs.count()):
                if self.tabs.isTabVisible(i):
                    self.tabs.setCurrentIndex(i)
                    break

        # Pass role to screens if they support it
        if hasattr(self.shipment_overview_screen, "set_current_role"):
            self.shipment_overview_screen.set_current_role(role)
        if hasattr(self.transport_screen, "set_current_role"):
            self.transport_screen.set_current_role(role)

    def _handle_tab_change(self, index: int) -> None:
        """Keep the transport workspace queue-first unless a shipment is explicitly opened."""
        target_widget = self.tabs.widget(index)
        if target_widget is self.transport_screen:
            self.transport_screen.show_default_overview()
        elif target_widget is self.warehouse_screen and not self._programmatic_switch:
            self._workflow_store.set_current_delivery(None)


def main() -> None:
    application = QApplication(sys.argv)
    apply_enterprise_light_theme(application)

    window = MainWindow()
    window.show()

    sys.exit(application.exec())


if __name__ == "__main__":
    main()
