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

# Clean (Light) Theme - Reference Match
LIGHT_THEME = ThemeColors(
    window="#eff6ff",            # Soft Blue-ish background (like Tailwind blue-50)
    window_text="#1e293b",       # Slate-800
    base="#ffffff",              # Pure White Cards
    alternate_base="#f8fafc",    # Slate-50
    text="#334155",              # Slate-700
    button="#e2e8f0",            # Slate-200
    button_text="#0f172a",       # Slate-900
    highlight="#3b82f6",         # Blue-500
    highlighted_text="#ffffff",
    border="#cbd5e1",            # Slate-300
    surface_container_low="#ffffff",
    surface_container="#ffffff",
    surface_container_high="#f1f5f9",
    card_border="#dbeafe",       # Blue-100 (Subtle border)
    shadow="rgba(148, 163, 184, 0.2)" # Blue-ish shadow
)

class ThemeManager:
    """Manages application-wide theme settings."""
    
    _current_theme = Theme.LIGHT

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
        """Apply Global QSS using the Reference Strategy (app.py)."""
        
        # Reference Gradient Background
        # "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #eaf2ff, stop:1 #dbe7ff);"
        
        qss = f"""
        QMainWindow {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #eaf2ff,
                stop:1 #dbe7ff
            );
        }}
        QWidget {{
            font-family: 'Segoe UI', sans-serif;
            font-size: 14px;
            color: #2c3e50;
        }}
        /* Global Button Styling from Reference */
        QPushButton {{
            padding: 8px 14px;
            border-radius: 10px;
            background-color: #4f8cff;
            color: white;
            border: none;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: #3a73e8;
        }}
        
        /* Dialogs need to stand out against the gradient */
        QDialog {{
            background: white;
            border-radius: 16px;
        }}
        
        /* Helper for specific labels */
        QLabel#mainTitle {{
            font-size: 32px;
            font-weight: 700;
            color: #2c3e50;
        }}

        /* Ghost / link-style navigation button (← Dashboard) */
        QPushButton#navLink {{
            background: transparent;
            border: 1px solid transparent;
            border-radius: 6px;
            color: #4f8cff;
            font-weight: 600;
            padding: 4px 10px;
        }}
        QPushButton#navLink:hover {{
            background: rgba(79, 140, 255, 0.12);
            border-color: rgba(79, 140, 255, 0.3);
            color: #2563eb;
        }}
        QPushButton#navLink:pressed {{
            background: rgba(79, 140, 255, 0.22);
        }}
        """
        app.setStyleSheet(qss)

    @classmethod
    def get_current_theme(cls) -> Theme:
        return cls._current_theme
