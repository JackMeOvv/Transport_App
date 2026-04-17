"""Reusable status badge widget."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


class StatusBadge(QLabel):
    """Small reusable badge for delivery, document, or print statuses."""

    def __init__(self, text: str, tone: str = "neutral", parent: object | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("StatusBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        """Update the badge tone."""
        self.setProperty("badgeTone", tone)
        self.style().unpolish(self)
        self.style().polish(self)
