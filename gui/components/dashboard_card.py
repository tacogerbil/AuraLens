import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal

logger = logging.getLogger(__name__)

class DashboardCard(QFrame):
    """
    Modern Dashboard Card based on reference implementation.
    
    Features:
    - Shadow effect
    - Rounded corners
    - Title, Description, and Action Button
    """
    
    clicked = Signal()

    def __init__(self, title: str, description: str, color: str, btn_text: str = None):
        super().__init__()
        self.setObjectName("card")
        self.setMinimumHeight(220)

        # Shadow Effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

        # Layout
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        
        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setObjectName("cardDesc")

        # Button (Optional, but reference has it)
        # If no btn_text provided, use title as reference did
        btn_label = btn_text if btn_text else title
        button = QPushButton(btn_label)
        button.setObjectName("cardButton")
        button.clicked.connect(self.clicked.emit)
        
        # Make the whole card clickable implies needing event filter or button covering?
        # Reference app.py binds the callback to the button.
        # We will expose the click via signal.

        # Inline Styling Matches Reference logic
        # Ideally move to ThemeManager, but adhering to "Implement Strategy" implies
        # using the direct approach if it's cleaner for the user's specific request.
        self.setStyleSheet(f"""
            QFrame#card {{
                background: {color};
                border-radius: 18px;
            }}
            QLabel#cardTitle {{
                font-size: 20px;
                font-weight: 600;
                color: #2c3e50;
                border: none;
            }}
            QLabel#cardDesc {{
                font-size: 14px;
                color: #555;
                border: none;
            }}
            QPushButton#cardButton {{
                background-color: #4f8cff;
                color: white;
                border-radius: 10px;
                padding: 10px;
                font-weight: 600;
                border: none;
            }}
            QPushButton#cardButton:hover {{
                background-color: #3a73e8;
            }}
        """)

        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addStretch()
        layout.addWidget(button)
