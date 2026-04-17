"""Stylesheet generation for the enterprise desktop theme."""

from __future__ import annotations

from logistics_app.desktop.ui.theme.tokens import DesignTokens, LIGHT_TOKENS


def build_light_stylesheet(tokens: DesignTokens = LIGHT_TOKENS) -> str:
    """Build the shared application stylesheet."""
    colors = tokens.colors
    spacing = tokens.spacing
    radius = tokens.radius
    typography = tokens.typography
    return f"""
    QWidget {{
        background: {colors.window_background};
        color: {colors.text_primary};
        font-family: {typography.font_family};
        font-size: {typography.size_body}pt;
    }}

    QWidget#AppShell,
    QWidget#ContentSurface,
    QFrame#CardSurface,
    QFrame#DocumentCard,
    QFrame#SummaryCard,
    QFrame#FilterBar,
    QFrame#ActionToolbar,
    QFrame#PageHeader,
    QDialog#BaseDialog {{
        background: {colors.surface_background};
        border: 1px solid {colors.border_subtle};
        border-radius: {radius.md}px;
    }}

    QWidget#PageRoot {{
        background: {colors.window_background};
    }}

    QLabel#PageTitle {{
        color: {colors.text_primary};
        font-size: {typography.size_page_title}pt;
        font-weight: {typography.weight_bold};
        background: transparent;
    }}

    QLabel#PageSubtitle,
    QLabel#SectionCaption,
    QLabel#MetaText {{
        color: {colors.text_secondary};
        font-size: {typography.size_body}pt;
        background: transparent;
    }}

    QLabel#SectionTitle {{
        color: {colors.text_primary};
        font-size: {typography.size_section}pt;
        font-weight: {typography.weight_semibold};
        background: transparent;
    }}

    QLabel#SummaryValue {{
        color: {colors.text_primary};
        font-size: 21pt;
        font-weight: {typography.weight_bold};
        background: transparent;
    }}

    QLabel#SummaryLabel {{
        color: {colors.text_secondary};
        font-size: {typography.size_body_large}pt;
        font-weight: {typography.weight_medium};
        background: transparent;
    }}

    QLabel#SummaryCaption,
    QLabel#DocumentMeta {{
        color: {colors.text_muted};
        font-size: {typography.size_caption}pt;
        background: transparent;
    }}

    QLabel#DocumentTitle {{
        color: {colors.text_primary};
        font-size: {typography.size_body_large}pt;
        font-weight: {typography.weight_semibold};
        background: transparent;
    }}

    QLabel#StatusBadge {{
        border-radius: {radius.pill}px;
        padding: 4px 10px;
        font-size: {typography.size_caption}pt;
        font-weight: {typography.weight_semibold};
    }}

    QLabel#StatusBadge[badgeTone="neutral"] {{
        background: {colors.badge_neutral_background};
        color: {colors.badge_neutral_text};
    }}

    QLabel#StatusBadge[badgeTone="success"] {{
        background: {colors.badge_success_background};
        color: {colors.badge_success_text};
    }}

    QLabel#StatusBadge[badgeTone="warning"] {{
        background: {colors.badge_warning_background};
        color: {colors.badge_warning_text};
    }}

    QLabel#StatusBadge[badgeTone="danger"] {{
        background: {colors.badge_danger_background};
        color: {colors.badge_danger_text};
    }}

    QLabel#StatusBadge[badgeTone="info"] {{
        background: {colors.badge_info_background};
        color: {colors.badge_info_text};
    }}

    QPushButton {{
        background: {colors.surface_background};
        border: 1px solid {colors.border_strong};
        border-radius: {radius.sm}px;
        padding: 8px 14px;
        min-height: 18px;
        font-weight: {typography.weight_medium};
    }}

    QPushButton:hover {{
        background: {colors.surface_alt_background};
    }}

    QPushButton:pressed {{
        background: #DCE5EE;
    }}

    QPushButton[buttonRole="primary"] {{
        background: {colors.accent};
        border: 1px solid {colors.accent};
        color: white;
    }}

    QPushButton[buttonRole="primary"]:hover {{
        background: {colors.accent_hover};
        border-color: {colors.accent_hover};
    }}

    QPushButton[buttonRole="primary"]:pressed {{
        background: {colors.accent_pressed};
        border-color: {colors.accent_pressed};
    }}

    QPushButton[buttonRole="danger"] {{
        background: {colors.danger};
        border: 1px solid {colors.danger};
        color: white;
    }}

    QPushButton[buttonRole="toolbar"] {{
        padding: 6px 12px;
    }}

    QLineEdit,
    QComboBox,
    QDateEdit,
    QTextEdit,
    QPlainTextEdit {{
        background: white;
        border: 1px solid {colors.border_strong};
        border-radius: {radius.sm}px;
        padding: 7px 10px;
        selection-background-color: {colors.selection_background};
        selection-color: {colors.selection_text};
    }}

    QLineEdit:focus,
    QComboBox:focus,
    QDateEdit:focus,
    QTextEdit:focus,
    QPlainTextEdit:focus {{
        border: 1px solid {colors.accent};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QToolButton {{
        background: transparent;
        border: none;
        padding: 6px 8px;
    }}

    QTableView,
    QTableWidget {{
        background: white;
        alternate-background-color: {colors.surface_alt_background};
        gridline-color: {colors.border_subtle};
        border: 1px solid {colors.border_subtle};
        border-radius: {radius.md}px;
        selection-background-color: {colors.selection_background};
        selection-color: {colors.selection_text};
    }}

    QHeaderView::section {{
        background: {colors.table_header_background};
        color: {colors.text_primary};
        border: none;
        border-right: 1px solid {colors.border_subtle};
        border-bottom: 1px solid {colors.border_subtle};
        padding: 10px 12px;
        font-weight: {typography.weight_semibold};
    }}

    QTableView::item,
    QTableWidget::item {{
        padding: 8px 10px;
        border: none;
    }}

    QTableView::item:hover,
    QTableWidget::item:hover {{
        background: {colors.table_row_hover};
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 12px;
        margin: 8px 0 8px 0;
    }}

    QScrollBar::handle:vertical {{
        background: {colors.border_strong};
        border-radius: 5px;
        min-height: 28px;
    }}

    QDialog#BaseDialog QLabel#DialogTitle {{
        font-size: {typography.size_section}pt;
        font-weight: {typography.weight_semibold};
        background: transparent;
    }}

    QDialog#BaseDialog QLabel#DialogMessage {{
        color: {colors.text_secondary};
        background: transparent;
    }}

    QProgressBar {{
        background: {colors.surface_alt_background};
        border: 1px solid {colors.border_subtle};
        border-radius: {radius.sm}px;
        text-align: center;
        min-height: 18px;
        color: {colors.text_primary};
        font-weight: {typography.weight_medium};
    }}

    QProgressBar::chunk {{
        background: {colors.accent};
        border-radius: {radius.sm - 1}px;
    }}

    QGroupBox {{
        background: {colors.surface_background};
        border: 1px solid {colors.border_subtle};
        border-radius: {radius.md}px;
        margin-top: 12px;
        padding-top: 10px;
        font-weight: {typography.weight_semibold};
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 6px;
        color: {colors.text_primary};
        background: {colors.surface_background};
    }}
    """
