"""Reusable page header widget."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class PageHeader(QWidget):
    """Page header with title, subtitle, and optional action area."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PageHeader")

        self._title_label = QLabel(title)
        self._title_label.setObjectName("PageTitle")

        self._subtitle_label = QLabel(subtitle)
        self._subtitle_label.setObjectName("PageSubtitle")
        self._subtitle_label.setWordWrap(True)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(6)
        text_layout.addWidget(self._title_label)
        text_layout.addWidget(self._subtitle_label)

        self._actions_layout = QHBoxLayout()
        self._actions_layout.setContentsMargins(0, 0, 0, 0)
        self._actions_layout.setSpacing(8)
        self._actions_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(20, 18, 20, 18)
        root_layout.setSpacing(20)
        root_layout.addLayout(text_layout, 1)
        root_layout.addLayout(self._actions_layout)

    def add_action_widget(self, widget: QWidget) -> None:
        """Add an action widget to the right side of the header."""
        self._actions_layout.addWidget(widget)

    def set_subtitle(self, subtitle: str) -> None:
        """Update the subtitle text."""
        self._subtitle_label.setText(subtitle)
