"""Reusable base dialog for enterprise workflows."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class BaseDialog(QDialog):
    """Common dialog shell with title, message area, and action row."""

    def __init__(
        self,
        title: str,
        message: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("BaseDialog")
        self.setModal(True)
        self.setWindowTitle(title)
        self.resize(520, 240)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("DialogTitle")

        self.message_label = QLabel(message)
        self.message_label.setObjectName("DialogMessage")
        self.message_label.setWordWrap(True)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)

        self.action_layout = QHBoxLayout()
        self.action_layout.setContentsMargins(0, 0, 0, 0)
        self.action_layout.setSpacing(8)
        self.action_layout.addStretch(1)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 22, 24, 20)
        root_layout.setSpacing(18)
        root_layout.addWidget(self.title_label)
        root_layout.addWidget(self.message_label)
        root_layout.addLayout(self.content_layout, 1)
        root_layout.addLayout(self.action_layout)

    def add_action_button(self, text: str, role: str = "default") -> QPushButton:
        """Add a footer button to the dialog."""
        button = QPushButton(text)
        if role != "default":
            button.setProperty("buttonRole", role)
        self.action_layout.addWidget(button)
        return button
