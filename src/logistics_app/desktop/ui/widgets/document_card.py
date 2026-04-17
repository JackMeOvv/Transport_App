"""Reusable document card widget."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from logistics_app.desktop.ui.widgets.status_badge import StatusBadge


class DocumentCard(QFrame):
    """Document card with metadata and common quick actions."""

    def __init__(
        self,
        title: str,
        filename: str,
        metadata: str,
        status_text: str,
        status_tone: str = "neutral",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("DocumentCard")

        title_label = QLabel(title)
        title_label.setObjectName("DocumentTitle")

        filename_label = QLabel(filename)
        filename_label.setObjectName("MetaText")
        filename_label.setWordWrap(True)

        metadata_label = QLabel(metadata)
        metadata_label.setObjectName("DocumentMeta")
        metadata_label.setWordWrap(True)

        self.open_button = QPushButton("Open")
        self.open_button.clicked.connect(self._on_action_clicked)
        self.print_button = QPushButton("Print")
        self.print_button.setProperty("buttonRole", "primary")
        self.print_button.clicked.connect(self._on_action_clicked)

        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)
        action_layout.addWidget(self.open_button)
        action_layout.addWidget(self.print_button)
        action_layout.addStretch(1)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(title_label)
        top_layout.addStretch(1)
        top_layout.addWidget(StatusBadge(status_text, status_tone))

        content_layout = QVBoxLayout(self)
        content_layout.setContentsMargins(18, 16, 18, 16)
        content_layout.setSpacing(8)
        content_layout.addLayout(top_layout)
        content_layout.addWidget(filename_label)
        content_layout.addWidget(metadata_label)
        content_layout.addSpacing(4)
        content_layout.addLayout(action_layout)

    def _on_action_clicked(self) -> None:
        """Demo placeholder for document actions."""
        pass
