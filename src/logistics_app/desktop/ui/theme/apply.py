"""Theme application helpers."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from logistics_app.desktop.ui.theme.styles import build_light_stylesheet
from logistics_app.desktop.ui.theme.tokens import LIGHT_TOKENS


def apply_enterprise_light_theme(application: QApplication) -> None:
    """Apply the shared enterprise light theme to the desktop application."""
    tokens = LIGHT_TOKENS
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(tokens.colors.window_background))
    palette.setColor(QPalette.ColorRole.Base, QColor(tokens.colors.surface_background))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(tokens.colors.surface_alt_background))
    palette.setColor(QPalette.ColorRole.Button, QColor(tokens.colors.surface_background))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(tokens.colors.text_primary))
    palette.setColor(QPalette.ColorRole.Text, QColor(tokens.colors.text_primary))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(tokens.colors.text_primary))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(tokens.colors.selection_background))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(tokens.colors.selection_text))
    application.setPalette(palette)
    application.setStyleSheet(build_light_stylesheet(tokens))
