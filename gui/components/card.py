"""
Card Component - MCCC Compliant
Provides a standardized container with depth, border, and optional accent color.
"""

from typing import Optional
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from gui.theme_manager import ThemeManager, Theme

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
        layout: Optional[QVBoxLayout] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        
        # Internal State
        self._title = title
        self._accent_color = accent_color
        
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
            
            # Decorator line if needed, or just let spacing handle it
            # self._inner_layout.addSpacing(5)

        # Apply Styles
        self._apply_style()
        
        # Shadow Effect
        # Note: Shadows can be expensive; disable if performance issues arise.
        # self._shadow = QGraphicsDropShadowEffect(self)
        # self._shadow.setBlurRadius(15)
        # self._shadow.setXOffset(0)
        # self._shadow.setYOffset(4)
        # self._shadow.setColor(QColor(0, 0, 0, 60))
        # self.setGraphicsEffect(self._shadow)

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
        theme = ThemeManager.get_current_theme()
        # We can't easily access the dataclass values here without importing the instances again
        # or making ThemeManager access them.
        # For now, we will rely on ThemeManager applying global QSS logic 
        # OR we fetch the specific colors if we make them accessible.
        
        # Ideally, ThemeManager should expose a 'get_stylesheet(widget_type)' or similar.
        # But for MCCC compliance, let's keep it simple and declarative here if possible,
        # or rely on the object names "Card" and "CardContent".
        
        # Inline styling for dynamic properties (accent color)
        accent_style = ""
        if self._accent_color:
            accent_style = f"border-top: 4px solid {self._accent_color};"
        
        self.setStyleSheet(f"""
            QFrame#CardContent {{
                border: none;
                background-color: palette(base); /* surface_container */
                border-radius: 8px;
            }}
            QFrame#Card {{
                background-color: transparent; /* Wrapper is transparent */
                border: 1px solid palette(mid); /* card_border */
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
