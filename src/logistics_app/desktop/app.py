"""Desktop application entry point."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
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
        self._programmatic_switch = False

        self.tabs = QTabWidget()
        self.shipment_overview_screen = ShipmentOverviewScreenWindow()
        self.warehouse_screen = WarehouseScreenWindow()
        self.transport_screen = TransportScreenWindow()

        self.tabs.addTab(self.shipment_overview_screen, "Shipment Overview")
        self.tabs.addTab(self.warehouse_screen, "Warehouse")
        self.tabs.addTab(self.transport_screen, "Transport")

        self.shipment_overview_screen.open_in_warehouse_requested.connect(self._open_in_warehouse)
        self.tabs.currentChanged.connect(self._handle_tab_change)

        self.setCentralWidget(self.tabs)

    def _open_in_warehouse(self, _delivery_slip_number: str) -> None:
        """Switch the shell to the warehouse workspace for the selected delivery."""
        self._programmatic_switch = True
        self.tabs.setCurrentWidget(self.warehouse_screen)
        self._programmatic_switch = False

    def _handle_tab_change(self, index: int) -> None:
        """Keep the transport workspace queue-first unless a shipment is explicitly opened."""
        if self.tabs.widget(index) is self.transport_screen:
            self.transport_screen.show_default_overview()

        if self.tabs.widget(index) is self.warehouse_screen and not self._programmatic_switch:
            self._workflow_store.set_current_delivery(None)


def main() -> None:
    application = QApplication(sys.argv)
    apply_enterprise_light_theme(application)

    window = MainWindow()
    window.show()

    sys.exit(application.exec())


if __name__ == "__main__":
    main()
