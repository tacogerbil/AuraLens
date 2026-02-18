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

# Protocol (Cyberpunk/Dark) Theme
DARK_THEME = ThemeColors(
    window="#1a1a1a",
    window_text="#e0e0e0",
    base="#121212",
    alternate_base="#2d2d2d",
    text="#e0e0e0",
    button="#333333",
    button_text="#ffffff",
    highlight="#007acc",  # VS Code Blue or similar
    highlighted_text="#ffffff",
    border="#444444"
)

# Clean (Light) Theme
LIGHT_THEME = ThemeColors(
    window="#f5f5f5",
    window_text="#1a1a1a",
    base="#ffffff",
    alternate_base="#f0f0f0",
    text="#1a1a1a",
    button="#e0e0e0",
    button_text="#000000",
    highlight="#007acc",
    highlighted_text="#ffffff",
    border="#cccccc"
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
        set_col(QPalette.ColorRole.Base, colors.base)
        set_col(QPalette.ColorRole.AlternateBase, colors.alternate_base)
        set_col(QPalette.ColorRole.ToolTipBase, colors.base)
        set_col(QPalette.ColorRole.ToolTipText, colors.text)
        set_col(QPalette.ColorRole.Text, colors.text)
        set_col(QPalette.ColorRole.Button, colors.button)
        set_col(QPalette.ColorRole.ButtonText, colors.button_text)
        set_col(QPalette.ColorRole.BrightText, "#ff0000") # Alert
        set_col(QPalette.ColorRole.Link, colors.highlight)
        set_col(QPalette.ColorRole.Highlight, colors.highlight)
        set_col(QPalette.ColorRole.HighlightedText, colors.highlighted_text)

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
            background-color: {colors.base};
            color: {colors.text};
            border: 1px solid {colors.border};
            border-radius: 4px;
            padding: 4px;
        }}
        QPushButton {{
            background-color: {colors.button};
            color: {colors.button_text};
            border: 1px solid {colors.border};
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
            background: {colors.border};
            min-height: 20px;
            border-radius: 5px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QSplitter::handle {{
            background-color: {colors.border};
            width: 1px;
        }}
        QToolTip {{
            background-color: {colors.base};
            color: {colors.text};
            border: 1px solid {colors.border};
        }}
        /* Tab Widget */
        QTabWidget::pane {{
            border: 1px solid {colors.border};
        }}
        QTabBar::tab {{
            background: {colors.button};
            color: {colors.button_text};
            padding: 8px 12px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        QTabBar::tab:selected {{
            background: {colors.base};
            border-bottom-color: {colors.base}; /* Blend with pane */
        }}
        """
        app.setStyleSheet(qss)

    @classmethod
    def get_current_theme(cls) -> Theme:
        return cls._current_theme
