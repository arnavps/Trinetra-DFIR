"""Centralized High-Contrast DFIR Workbench theme tokens and badge stylesheets."""

DFIR_DARK_THEME = {
    "bg_color": "#0D1117",
    "card_bg": "#161B22",
    "border_color": "#30363D",
    "text_color": "#C9D1D9",
    "text_bright": "#F0F6FC",
    "text_muted": "#8B949E",
    "accent_blue": "#1F6FEB",
    "accent_cyan": "#58A6FF",
    "status_emerald_bg": "#0D3321",
    "status_emerald_fg": "#3FB950",
    "status_amber_bg": "#3A2404",
    "status_amber_fg": "#F0883E",
    "status_cyan_bg": "#0C2D48",
    "status_cyan_fg": "#38BDF8",
    "font_main": "'Segoe UI', -apple-system, sans-serif",
    "font_mono": "'Consolas', 'JetBrains Mono', 'Courier New', monospace",
}

DARK_THEME = DFIR_DARK_THEME
LIGHT_THEME = DFIR_DARK_THEME


def get_badge_stylesheet(bg: str, fg: str, border: str = "transparent") -> str:
    """Generates small pill badge QSS styling."""
    return f"""
        background-color: {bg};
        color: {fg};
        border: 1px solid {border if border != 'transparent' else fg};
        border-radius: 4px;
        padding: 2px 6px;
        font-family: 'Consolas', monospace;
        font-weight: bold;
        font-size: 11px;
    """
