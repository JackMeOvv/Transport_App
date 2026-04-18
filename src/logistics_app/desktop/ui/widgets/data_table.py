"""Reusable table helpers for operational grids."""

from __future__ import annotations

from PySide6.QtCore import Qt
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

    def _show_header_menu(self, pos) -> None:
        """Show a context menu to toggle column visibility."""
        header = self.horizontalHeader()
        menu = QMenu(self)

        for i in range(self.columnCount()):
            column_name = self.horizontalHeaderItem(i).text()
            action = QAction(column_name, menu)
            action.setCheckable(True)
            action.setChecked(not self.isColumnHidden(i))
            action.triggered.connect(lambda checked, col=i: self.setColumnHidden(col, not checked))
            menu.addAction(action)

        menu.exec(header.mapToGlobal(pos))
