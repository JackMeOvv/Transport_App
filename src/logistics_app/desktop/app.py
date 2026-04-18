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
from logistics_app.desktop.ui.theme import apply_enterprise_light_theme
from logistics_app.desktop.workflow import get_workflow_store


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Logistics App")
        self.resize(1400, 900)

        self._workflow_store = get_workflow_store()
        self._workflow_store.workflow_changed.connect(self._update_tab_visibility)

        self.tabs = QTabWidget()
        self.shipment_overview_screen = ShipmentOverviewScreenWindow()
        self.warehouse_screen = WarehouseScreenWindow()
        self.transport_screen = TransportScreenWindow()

        self.tabs.addTab(self.shipment_overview_screen, "Shipment Overview")
        self.tabs.addTab(self.warehouse_screen, "Warehouse")
        self.tabs.addTab(self.transport_screen, "Transport")

        self.shipment_overview_screen.open_in_warehouse_requested.connect(self._open_in_warehouse)
        self.tabs.currentChanged.connect(self._handle_tab_change)

        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Simple Role Switcher Header
        role_switcher_bar = QWidget()
        role_switcher_bar.setObjectName("RoleSwitcherBar")
        role_switcher_bar.setStyleSheet("background-color: #f8f9fa; border-bottom: 1px solid #dee2e6;")
        role_layout = QHBoxLayout(role_switcher_bar)
        role_layout.setContentsMargins(16, 8, 16, 8)
        role_layout.addWidget(QLabel("Select Active Role (Demo):"))
        self.role_selector = QComboBox()
        self.role_selector.addItems(["admin", "warehouse", "transport"])
        self.role_selector.setCurrentText(self._workflow_store.user_role())
        self.role_selector.currentTextChanged.connect(self._workflow_store.set_user_role)
        role_layout.addWidget(self.role_selector)
        role_layout.addStretch(1)

        main_layout.addWidget(role_switcher_bar)
        main_layout.addWidget(self.tabs)

        self.setCentralWidget(main_container)
        self._update_tab_visibility()

    def _open_in_warehouse(self, _delivery_slip_number: str) -> None:
        """Switch the shell to the warehouse workspace for the selected delivery."""
        self.tabs.setCurrentWidget(self.warehouse_screen)

    def _handle_tab_change(self, index: int) -> None:
        """Keep the transport workspace queue-first unless a shipment is explicitly opened."""
        if index < 0:
            return
        if self.tabs.widget(index) is self.transport_screen:
            self.transport_screen.show_default_overview()

    def _update_tab_visibility(self) -> None:
        """Show/hide tabs based on the active user role."""
        role = self._workflow_store.user_role()

        # Mapping tabs to their index/existence is tricky when hiding.
        # Simple approach: remove all and re-add based on role.
        current_widget = self.tabs.currentWidget()

        # Store all tabs
        all_tabs = [
            (self.shipment_overview_screen, "Shipment Overview"),
            (self.warehouse_screen, "Warehouse"),
            (self.transport_screen, "Transport"),
        ]

        self.tabs.blockSignals(True)
        self.tabs.clear()

        if role == "admin":
            for widget, title in all_tabs:
                self.tabs.addTab(widget, title)
        elif role == "warehouse":
            self.tabs.addTab(self.warehouse_screen, "Warehouse")
        elif role == "transport":
            self.tabs.addTab(self.transport_screen, "Transport")

        if current_widget:
            self.tabs.setCurrentWidget(current_widget)
        if self.tabs.currentIndex() < 0 and self.tabs.count() > 0:
            self.tabs.setCurrentIndex(0)
        self.tabs.blockSignals(False)


def main() -> None:
    application = QApplication(sys.argv)
    apply_enterprise_light_theme(application)

    window = MainWindow()
    window.show()

    sys.exit(application.exec())


if __name__ == "__main__":
    main()
