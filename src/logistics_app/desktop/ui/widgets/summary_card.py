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

        label_widget = QLabel(label)
        label_widget.setObjectName("SummaryLabel")

        value_widget = QLabel(value)
        value_widget.setObjectName("SummaryValue")

        caption_widget = QLabel(caption)
        caption_widget.setObjectName("SummaryCaption")
        caption_widget.setWordWrap(True)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(label_widget)
        header_layout.addStretch(1)
        if badge_text:
            header_layout.addWidget(StatusBadge(badge_text, badge_tone))

        body_layout = QVBoxLayout(self)
        body_layout.setContentsMargins(18, 18, 18, 18)
        body_layout.setSpacing(6)
        body_layout.addLayout(header_layout)
        body_layout.addWidget(value_widget)
        body_layout.addWidget(caption_widget)
