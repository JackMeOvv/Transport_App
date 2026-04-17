"""Reusable action toolbar widget."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget


class ActionToolbar(QFrame):
    """Action toolbar for high-frequency operational commands."""

    def __init__(self, title: str = "Actions", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ActionToolbar")

        self._title_label = QLabel(title)
        self._title_label.setObjectName("SectionTitle")

        self._actions_layout = QHBoxLayout()
        self._actions_layout.setContentsMargins(0, 0, 0, 0)
        self._actions_layout.setSpacing(8)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)
        layout.addWidget(self._title_label)
        layout.addStretch(1)
        layout.addLayout(self._actions_layout)

    def add_button(self, text: str, role: str = "toolbar") -> QPushButton:
        """Create and add a toolbar button."""
        button = QPushButton(text)
        button.setProperty("buttonRole", role)
        self._actions_layout.addWidget(button)
        return button
