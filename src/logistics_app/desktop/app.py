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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Logistics App")
        self.resize(1400, 900)

        tabs = QTabWidget()
        tabs.addTab(ShipmentOverviewScreenWindow(), "Shipment Overview")
        tabs.addTab(WarehouseScreenWindow(), "Warehouse")
        tabs.addTab(TransportScreenWindow(), "Transport")

        self.setCentralWidget(tabs)


def main() -> None:
    application = QApplication(sys.argv)
    apply_enterprise_light_theme(application)

    window = MainWindow()
    window.show()

    sys.exit(application.exec())


if __name__ == "__main__":
    main()
