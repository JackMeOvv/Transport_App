"""Design tokens for the enterprise desktop light theme."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ColorPalette:
    """Central color palette for the desktop client."""

    window_background: str = "#F4F7FA"
    surface_background: str = "#FFFFFF"
    surface_alt_background: str = "#EEF3F8"
    border_subtle: str = "#D7E0EA"
    border_strong: str = "#BCC9D6"
    text_primary: str = "#1F2A37"
    text_secondary: str = "#526273"
    text_muted: str = "#6B7C8F"
    accent: str = "#0F5B99"
    accent_hover: str = "#0C4F86"
    accent_pressed: str = "#083E69"
    success: str = "#227A52"
    warning: str = "#B57411"
    danger: str = "#B13B34"
    info: str = "#1D5E91"
    badge_neutral_background: str = "#E9EFF5"
    badge_neutral_text: str = "#445464"
    badge_success_background: str = "#E3F3EB"
    badge_success_text: str = "#206A49"
    badge_warning_background: str = "#FFF2D9"
    badge_warning_text: str = "#8C5A0E"
    badge_danger_background: str = "#FBE5E3"
    badge_danger_text: str = "#98332E"
    badge_info_background: str = "#E2EEF8"
    badge_info_text: str = "#1C5988"
    selection_background: str = "#D8E8F6"
    selection_text: str = "#16324A"
    table_header_background: str = "#EAF0F6"
    table_row_hover: str = "#F5F9FD"


@dataclass(frozen=True, slots=True)
class SpacingScale:
    """Shared spacing scale for consistent rhythm."""

    xxs: int = 4
    xs: int = 8
    sm: int = 12
    md: int = 16
    lg: int = 20
    xl: int = 24
    xxl: int = 32


@dataclass(frozen=True, slots=True)
class RadiusScale:
    """Shared radius scale for panels, buttons, and badges."""

    sm: int = 6
    md: int = 10
    lg: int = 14
    pill: int = 999


@dataclass(frozen=True, slots=True)
class TypographyScale:
    """Windows-friendly typography scale."""

    font_family: str = '"Segoe UI Variable","Segoe UI","Arial"'
    size_caption: int = 11
    size_body: int = 12
    size_body_large: int = 13
    size_section: int = 18
    size_page_title: int = 26
    weight_regular: int = 400
    weight_medium: int = 500
    weight_semibold: int = 600
    weight_bold: int = 700


@dataclass(frozen=True, slots=True)
class DesignTokens:
    """Full set of desktop design tokens."""

    colors: ColorPalette = field(default_factory=ColorPalette)
    spacing: SpacingScale = field(default_factory=SpacingScale)
    radius: RadiusScale = field(default_factory=RadiusScale)
    typography: TypographyScale = field(default_factory=TypographyScale)


LIGHT_TOKENS = DesignTokens()
