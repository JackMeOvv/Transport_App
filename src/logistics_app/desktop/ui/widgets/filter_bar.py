"""Reusable operational filter bar."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


class FilterBar(QFrame):
    """Practical filter bar for operational list screens."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FilterBar")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search delivery slip, pallet, or document")

        self.status_filter = QComboBox()
        self.status_filter.addItem("All statuses")

        self.type_filter = QComboBox()
        self.type_filter.addItem("All types")

        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True)

        self.apply_button = QPushButton("Apply")
        self.apply_button.setProperty("buttonRole", "primary")
        self.clear_button = QPushButton("Clear")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        layout.addWidget(self._caption("Search"))
        layout.addWidget(self.search_input, 2)
        layout.addWidget(self._caption("Status"))
        layout.addWidget(self.status_filter)
        layout.addWidget(self._caption("Type"))
        layout.addWidget(self.type_filter)
        layout.addWidget(self._caption("Date"))
        layout.addWidget(self.date_filter)
        layout.addStretch(1)
        layout.addWidget(self.clear_button)
        layout.addWidget(self.apply_button)

    def _caption(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionCaption")
        return label
