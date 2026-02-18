"""
Card Component - MCCC Compliant
Provides a standardized container with depth, border, and optional accent color.
"""

from typing import Optional
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from gui.theme_manager import ThemeManager, Theme, LIGHT_THEME, DARK_THEME

class Card(QFrame):
    """
    A unified Card container that adheres to the application's theme.
    
    Features:
    - Consistent background and border (from ThemeManager).
    - Optional title header.
    - Optional colored accent strip (top).
    - Elevation (shadow).
    """

    def __init__(
        self,
        title: Optional[str] = None,
        accent_color: Optional[str] = None,
        border_color: Optional[str] = None,
        layout: Optional[QVBoxLayout] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        
        # Internal State
        self._title = title
        self._accent_color = accent_color
        self._border_color = border_color
        
        # Layout Setup
        self._layout = layout if layout else QVBoxLayout()
        self._layout.setContentsMargins(1, 1, 1, 1) # Thin wrapper
        self.setLayout(self._layout)
        
        # Content Container (Inner Frame) allows for proper padding inside the border/accent
        self._content_packet = QFrame()
        self._content_packet.setObjectName("CardContent")
        self._inner_layout = QVBoxLayout(self._content_packet)
        self._inner_layout.setContentsMargins(16, 16, 16, 16)
        self._inner_layout.setSpacing(10)
        self._layout.addWidget(self._content_packet)

        # Optional Title
        if self._title:
            self._title_label = QLabel(self._title)
            self._title_label.setObjectName("CardTitle")
            self._title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self._inner_layout.addWidget(self._title_label)

        # Apply Styles
        self._apply_style()
        
        # Shadow Effect
        # Enabled for Light Theme depth
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(20)
        self._shadow.setXOffset(0)
        self._shadow.setYOffset(4)
        
        # Fetch shadow color from current theme
        current_theme_colors = DARK_THEME if ThemeManager.get_current_theme() == Theme.DARK else LIGHT_THEME
        
        # Parse rgba string or hex. ThemeManager uses rgba(...) string for shadow in standard theme.
        # But QColor needs distinct args or a proper string.
        # QColor("rgba(r,g,b,a)") works in Qt6.
        # We can extract it from the theme object.
        shadow_color_str = current_theme_colors.shadow
        
        # QColor constructor handles "rgba(...)" strings if they are formatted correctly?
        # Actually QColor(name) handles #RRGGBB. It might not handle rgba(...) css syntax directly in all versions.
        # Let's use a safe fallback or a helper if uncertain.
        # However, for now, let's use the hardcoded safe value I had before, BUT properly selected based on theme.
        
        # We will use the theme's shadow string if it passes QColor check, otherwise fallback.
        # The simplest fix for the crash is just using the imported variables.
        # And let's stick to the safe manual QColor for now to ensure no parsing crash.
        
        if ThemeManager.get_current_theme() == Theme.DARK:
             self._shadow.setColor(QColor(0, 0, 0, 128)) 
        else:
             self._shadow.setColor(QColor(148, 163, 184, 50)) # Blue-ish shadow for Light mode
             
        self.setGraphicsEffect(self._shadow)

    def add_widget(self, widget: QWidget) -> None:
        """Add a widget to the card's content area."""
        self._inner_layout.addWidget(widget)

    def add_layout(self, layout: QVBoxLayout) -> None:
        """Add a layout to the card's content area."""
        self._inner_layout.addLayout(layout)
        
    def add_stretch(self) -> None:
        """Add vertical stretch to content."""
        self._inner_layout.addStretch()

    def set_content_layout(self, layout: QVBoxLayout) -> None:
        """Replace the inner layout (use with caution)."""
        QWidget().setLayout(self._inner_layout) # Delete old
        self._inner_layout = layout
        self._content_packet.setLayout(self._inner_layout)

    def _apply_style(self) -> None:
        """Apply the specific QSS for this card."""
        
        # Inline styling for dynamic properties (accent color / border color)
        accent_style = ""
        border_style = "border: 1px solid palette(mid);" # Default
        
        if self._accent_color:
            accent_style = f"border-top: 4px solid {self._accent_color};"
            
        if self._border_color:
             # Override default border with specific color (e.g. for Action Cards)
             border_style = f"border: 2px solid {self._border_color};"
        
        self.setStyleSheet(f"""
            QFrame#CardContent {{
                border: none;
                background-color: palette(base); /* surface_container */
                border-radius: 8px;
            }}
            QFrame#Card {{
                background-color: transparent; /* Wrapper is transparent */
                {border_style} /* card_border or override */
                border-radius: 8px;
                {accent_style}
            }}
            QLabel#CardTitle {{
                font-size: 16px;
                font-weight: bold;
                color: palette(text);
                margin-bottom: 8px;
            }}
        """)
