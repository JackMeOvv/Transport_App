"""Reusable document card widget."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from logistics_app.desktop.ui.widgets.status_badge import StatusBadge


class DocumentCard(QFrame):
    """Document card with metadata and common quick actions."""

    open_requested = Signal(str)
    print_requested = Signal(str)

    def __init__(
        self,
        title: str,
        filename: str,
        metadata: str,
        status_text: str,
        status_tone: str = "neutral",
        can_open: bool = True,
        can_print: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("DocumentCard")
        self.title = title

        self.title_label = QLabel(title)
        self.title_label.setObjectName("DocumentTitle")

        self.filename_label = QLabel(filename)
        self.filename_label.setObjectName("MetaText")
        self.filename_label.setWordWrap(True)

        self.metadata_label = QLabel(metadata)
        self.metadata_label.setObjectName("DocumentMeta")
        self.metadata_label.setWordWrap(True)

        self.status_badge = StatusBadge(status_text, status_tone)

        self.open_button = QPushButton("Open")
        self.open_button.clicked.connect(lambda: self.open_requested.emit(self.title))
        self.open_button.setEnabled(can_open)
        self.print_button = QPushButton("Print")
        self.print_button.setProperty("buttonRole", "primary")
        self.print_button.clicked.connect(lambda: self.print_requested.emit(self.title))
        self.print_button.setEnabled(can_print)

        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)
        action_layout.addWidget(self.open_button)
        action_layout.addWidget(self.print_button)
        action_layout.addStretch(1)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(self.title_label)
        top_layout.addStretch(1)
        top_layout.addWidget(self.status_badge)

        content_layout = QVBoxLayout(self)
        content_layout.setContentsMargins(18, 16, 18, 16)
        content_layout.setSpacing(8)
        content_layout.addLayout(top_layout)
        content_layout.addWidget(self.filename_label)
        content_layout.addWidget(self.metadata_label)
        content_layout.addSpacing(4)
        content_layout.addLayout(action_layout)

    def set_filename(self, filename: str) -> None:
        """Update the displayed filename."""
        self.filename_label.setText(filename)

    def set_metadata(self, metadata: str) -> None:
        """Update the metadata description."""
        self.metadata_label.setText(metadata)

    def set_status(self, status_text: str, status_tone: str) -> None:
        """Update the status badge."""
        self.status_badge.setText(status_text)
        self.status_badge.set_tone(status_tone)

    def set_action_availability(self, can_open: bool, can_print: bool) -> None:
        """Enable or disable quick actions based on document availability."""
        self.open_button.setEnabled(can_open)
        self.print_button.setEnabled(can_print)
