"""Theme Manager for AuraLens - Handles Dark/Light mode and color palettes."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

class Theme(Enum):
    DARK = auto()
    LIGHT = auto()

@dataclass
class ThemeColors:
    window: str
    window_text: str
    base: str
    alternate_base: str
    text: str
    button: str
    button_text: str
    highlight: str
    highlighted_text: str
    border: str
    # New Semantic Roles for Depth
    surface_container_low: str   # Lowest depth (background)
    surface_container: str       # Standard container (cards)
    surface_container_high: str  # Higher depth (dialogs/popovers)
    card_border: str             # Specific border for cards
    shadow: str                  # Shadow color

# Protocol (Cyberpunk/Dark) Theme
DARK_THEME = ThemeColors(
    window="#0f0f12",            # Darker, slightly blue-tinted background
    window_text="#e0e0e0",
    base="#1a1b1e",             # Card background
    alternate_base="#25262b",    # Hover/Active states
    text="#c9d1d9",
    button="#2c2e33",
    button_text="#ffffff",
    highlight="#3b82f6",         # Bright Blue
    highlighted_text="#ffffff",
    border="#30363d",            # General borders
    surface_container_low="#0d1117",
    surface_container="#161b22",
    surface_container_high="#21262d",
    card_border="#30363d",
    shadow="rgba(0, 0, 0, 0.5)"
)

# Clean (Light) Theme
LIGHT_THEME = ThemeColors(
    window="#f0f2f5",            # Light gray background (like macOS/iOS grouptable)
    window_text="#1a1a1a",
    base="#ffffff",              # Card background
    alternate_base="#f8f9fa",
    text="#1a1a1a",
    button="#e2e8f0",
    button_text="#0f172a",
    highlight="#3b82f6",
    highlighted_text="#ffffff",
    border="#e2e8f0",
    surface_container_low="#ffffff",
    surface_container="#ffffff",
    surface_container_high="#f8fafc",
    card_border="#cbd5e1",      # Distinct border for light mode cards
    shadow="rgba(0, 0, 0, 0.1)"
)

class ThemeManager:
    """Manages application-wide theme settings."""
    
    _current_theme = Theme.DARK

    @classmethod
    def apply_theme(cls, app: QApplication, theme: Theme = Theme.DARK) -> None:
        """Apply the specified theme to the application."""
        cls._current_theme = theme
        colors = DARK_THEME if theme == Theme.DARK else LIGHT_THEME
        
        palette = QPalette()
        
        # Helper to set color
        def set_col(arg1, arg2, arg3=None):
            """
            Set palette color.
            Usage:
                set_col(role, hex_code)
                set_col(group, role, hex_code)
            """
            if arg3 is None:
                # overload: role, hex_code
                role, hex_code = arg1, arg2
                palette.setColor(role, QColor(hex_code))
            else:
                # overload: group, role, hex_code
                group, role, hex_code = arg1, arg2, arg3
                palette.setColor(group, role, QColor(hex_code))

        # Standard Palette Mapping
        set_col(QPalette.ColorRole.Window, colors.window)
        set_col(QPalette.ColorRole.WindowText, colors.window_text)
        set_col(QPalette.ColorRole.Base, colors.surface_container) # Card Background
        set_col(QPalette.ColorRole.AlternateBase, colors.alternate_base)
        set_col(QPalette.ColorRole.ToolTipBase, colors.surface_container_high)
        set_col(QPalette.ColorRole.ToolTipText, colors.text)
        set_col(QPalette.ColorRole.Text, colors.text)
        set_col(QPalette.ColorRole.Button, colors.button)
        set_col(QPalette.ColorRole.ButtonText, colors.button_text)
        set_col(QPalette.ColorRole.BrightText, "#ff0000") # Alert
        set_col(QPalette.ColorRole.Link, colors.highlight)
        set_col(QPalette.ColorRole.Highlight, colors.highlight)
        set_col(QPalette.ColorRole.HighlightedText, colors.highlighted_text)
        
        # Mapping Card Border to 'Mid' for QSS usage in Card component
        set_col(QPalette.ColorRole.Mid, colors.card_border)

        # Disabled state
        set_col(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, "#777777")
        set_col(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, "#777777")
        set_col(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, "#777777")

        app.setPalette(palette)
        
        # Apply global stylesheet for specific widgets that ignore Palette
        cls._apply_stylesheet(app, colors)

    @classmethod
    def _apply_stylesheet(cls, app: QApplication, colors: ThemeColors) -> None:
        """Apply QSS using the color palette."""
        qss = f"""
        QMainWindow {{
            background-color: {colors.window};
        }}
        QWidget {{
            background-color: {colors.window};
            color: {colors.text};
            font-family: 'Segoe UI', sans-serif;
            font-size: 14px;
        }}
        QFrame {{
            border: none;
        }}
        /* Specific overrides for commonly styled widgets */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {colors.surface_container}; /* Match Card background */
            color: {colors.text};
            border: 1px solid {colors.card_border};
            border-radius: 4px;
            padding: 4px;
        }}
        QPushButton {{
            background-color: {colors.button};
            color: {colors.button_text};
            border: 1px solid {colors.card_border};
            border-radius: 4px;
            padding: 6px 12px;
        }}
        QPushButton:hover {{
            background-color: {colors.highlight};
            color: {colors.highlighted_text};
            border: 1px solid {colors.highlight};
        }}
        QPushButton:pressed {{
            background-color: {colors.highlight}; /* Darker? */
        }}
        QScrollBar:vertical {{
            border: none;
            background: {colors.window};
            width: 10px;
            margin: 0px 0px 0px 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {colors.card_border};
            min-height: 20px;
            border-radius: 5px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QSplitter::handle {{
            background-color: {colors.card_border};
            width: 1px;
        }}
        QToolTip {{
            background-color: {colors.surface_container_high};
            color: {colors.text};
            border: 1px solid {colors.card_border};
        }}
        /* Tab Widget */
        QTabWidget::pane {{
            border: 1px solid {colors.card_border};
        }}
        QTabBar::tab {{
            background: {colors.button};
            color: {colors.button_text};
            padding: 8px 12px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        QTabBar::tab:selected {{
            background: {colors.surface_container};
            border-bottom-color: {colors.surface_container}; /* Blend with pane */
        }}
        """
        app.setStyleSheet(qss)

    @classmethod
    def get_current_theme(cls) -> Theme:
        return cls._current_theme
