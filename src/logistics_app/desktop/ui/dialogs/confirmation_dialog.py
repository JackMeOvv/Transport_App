"""Reusable confirmation dialog."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from logistics_app.desktop.ui.dialogs.base_dialog import BaseDialog


class ConfirmationDialog(BaseDialog):
    """Simple confirmation dialog with primary and secondary actions."""

    def __init__(
        self,
        title: str,
        message: str,
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title=title, message=message, parent=parent)
        self.cancel_button = self.add_action_button(cancel_text)
        self.confirm_button = self.add_action_button(confirm_text, role="primary")
        self.cancel_button.clicked.connect(self.reject)
        self.confirm_button.clicked.connect(self.accept)
