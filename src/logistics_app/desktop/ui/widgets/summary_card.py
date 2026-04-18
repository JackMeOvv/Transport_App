"""Reusable summary card widget."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from logistics_app.desktop.ui.widgets.status_badge import StatusBadge


class SummaryCard(QFrame):
    """Compact operational summary card for KPI-style metrics."""

    def __init__(
        self,
        label: str,
        value: str,
        caption: str = "",
        badge_text: str | None = None,
        badge_tone: str = "neutral",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SummaryCard")

        self.label_widget = QLabel(label)
        self.label_widget.setObjectName("SummaryLabel")

        self.value_widget = QLabel(value)
        self.value_widget.setObjectName("SummaryValue")

        self.caption_widget = QLabel(caption)
        self.caption_widget.setObjectName("SummaryCaption")
        self.caption_widget.setWordWrap(True)
        self.badge_widget = StatusBadge(badge_text, badge_tone) if badge_text else None

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(self.label_widget)
        header_layout.addStretch(1)
        if self.badge_widget is not None:
            header_layout.addWidget(self.badge_widget)

        body_layout = QVBoxLayout(self)
        body_layout.setContentsMargins(18, 18, 18, 18)
        body_layout.setSpacing(6)
        body_layout.addLayout(header_layout)
        body_layout.addWidget(self.value_widget)
        body_layout.addWidget(self.caption_widget)

    def update_content(
        self,
        label: str,
        value: str,
        caption: str,
        badge_text: str | None = None,
        badge_tone: str = "neutral",
    ) -> None:
        """Update the card content after construction."""
        self.label_widget.setText(label)
        self.value_widget.setText(value)
        self.caption_widget.setText(caption)
        if badge_text is not None:
            if self.badge_widget is None:
                self.badge_widget = StatusBadge(badge_text, badge_tone, self)
                self.layout().itemAt(0).layout().addWidget(self.badge_widget)
            else:
                self.badge_widget.setText(badge_text)
                self.badge_widget.set_tone(badge_tone)
