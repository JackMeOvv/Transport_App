"""Reusable table helpers for operational grids."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QMenu, QTableWidget, QWidget


class DataTable(QTableWidget):
    """Enterprise-styled table widget for list screens."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        self.setSortingEnabled(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setMinimumSectionSize(90)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self._show_header_menu)
        self.horizontalHeader().sectionResized.connect(self._save_column_state)

    def _save_column_state(self) -> None:
        """Persist header state (widths and visibility) to application settings."""
        if not self.objectName():
            return
        settings = QSettings("InternalLogistics", "DesktopClient")
        settings.setValue(f"DataTable/{self.objectName()}/HeaderState", self.horizontalHeader().saveState())

    def showEvent(self, event) -> None:
        """Restore header state when the widget is first shown."""
        super().showEvent(event)
        if not self.objectName():
            return
        settings = QSettings("InternalLogistics", "DesktopClient")
        state = settings.value(f"DataTable/{self.objectName()}/HeaderState")
        if state:
            self.horizontalHeader().restoreState(state)

    def _show_header_menu(self, pos) -> None:
        """Show a context menu to toggle column visibility."""
        header = self.horizontalHeader()
        menu = QMenu(self)

        for i in range(self.columnCount()):
            column_name = self.horizontalHeaderItem(i).text()
            action = QAction(column_name, menu)
            action.setCheckable(True)
            action.setChecked(not self.isColumnHidden(i))
            action.triggered.connect(lambda checked, col=i: self._toggle_column(col, checked))
            menu.addAction(action)

        menu.exec(header.mapToGlobal(pos))

    def _toggle_column(self, column: int, visible: bool) -> None:
        """Toggle column visibility and save state."""
        self.setColumnHidden(column, not visible)
        self._save_column_state()
