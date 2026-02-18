"""Home Screen Dashboard with Navigation Cards and Recent Files."""

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QPushButton,
    QScrollArea,
    QSpacerItem,
    QSizePolicy
)

from gui.theme_manager import ThemeManager

class HomeCard(QFrame):
    """Interactive Card for Home Screen Actions."""
    
    clicked = Signal()

    def __init__(self, title: str, description: str, icon_name: str, action_text: str, color_accent: str):
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("HomeCard")
        
        # Dimensions
        self.setFixedSize(220, 260)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Icon Area (Placeholder for now, using color circle or text)
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(64, 64)
        self._icon_label.setStyleSheet(f"""
            background-color: {color_accent};
            border-radius: 32px;
            color: white;
            font-size: 24px;
            font-weight: bold;
        """)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setText(icon_name[:1]) # First letter as icon
        layout.addWidget(self._icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Title
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)
        
        # Description
        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setStyleSheet("color: #888888; font-size: 13px;")
        layout.addWidget(desc_lbl)
        
        layout.addStretch()
        
        # Action Button (Visual only, whole card is clickable)
        action_btn = QPushButton(action_text)
        action_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_accent};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color_accent}DD; 
            }}
        """)
        action_btn.clicked.connect(self.clicked)
        # Pass clicks through to card?
        button_layout = QHBoxLayout()
        button_layout.addWidget(action_btn)
        layout.addLayout(button_layout)

        # Style the card itself
        self.setStyleSheet("""
            QFrame#HomeCard {
                background-color: palette(base);
                border: 1px solid palette(mid);
                border-radius: 12px;
            }
            QFrame#HomeCard:hover {
                border: 1px solid palette(highlight);
                background-color: palette(alternate-base);
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

class RecentFileRow(QFrame):
    """Row item for Recent Files list."""
    
    open_requested = Signal(Path)

    def __init__(self, path: Path, date_str: str):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Icon
        icon_lbl = QLabel("PDF")
        icon_lbl.setFixedSize(32, 32)
        icon_lbl.setStyleSheet("background-color: #e81123; color: white; border-radius: 4px; padding: 4px;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)
        
        # Details
        info_layout = QVBoxLayout()
        name_lbl = QLabel(path.name)
        name_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        path_lbl = QLabel(str(path.parent))
        path_lbl.setStyleSheet("color: #888888; font-size: 12px;")
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(path_lbl)
        layout.addLayout(info_layout)
        
        layout.addStretch()
        
        # Date
        date_lbl = QLabel(date_str)
        date_lbl.setStyleSheet("color: #888888;")
        layout.addWidget(date_lbl)
        
        # Delete/Remove button (visual only for now)
        del_btn = QPushButton("✕")
        del_btn.setFlat(True)
        del_btn.setFixedSize(24, 24)
        layout.addWidget(del_btn)

        self.path = path
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit(self.path)

class HomeScreen(QWidget):
    """Main Dashboard Widget."""

    action_open_pdf = Signal()
    action_process_pdf = Signal()
    action_test_prompt = Signal()
    action_config = Signal()
    
    def __init__(self, recent_files: List[Path] = None):
        super().__init__()
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(30)
        
        # Header
        header = QLabel("PDF Processor")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: palette(text);")
        main_layout.addWidget(header)
        
        # Current File Indicator
        self._current_file_label = QLabel("No file loaded")
        self._current_file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._current_file_label.setStyleSheet("color: palette(midlight); font-size: 14px;")
        main_layout.addWidget(self._current_file_label)
        
        # Cards Grid
        cards_layout = QGridLayout()
        cards_layout.setSpacing(20)
        
        # Card 1: Open PDF
        self.card_open = HomeCard(
            "Open PDF", 
            "Select a PDF file to open and begin processing.",
            "folder", "Open PDF", "#3b82f6"
        )
        self.card_open.clicked.connect(self.action_open_pdf)
        cards_layout.addWidget(self.card_open, 0, 0)
        
        # Card 2: Process PDF
        self.card_process = HomeCard(
            "Process PDF",
            "Run OCR on the PDF to extract and verify text.",
            "settings", "Process PDF", "#10b981"
        )
        self.card_process.clicked.connect(self.action_process_pdf)
        cards_layout.addWidget(self.card_process, 0, 1)

        # Card 3: Test Prompt
        self.card_test = HomeCard(
            "Test Prompt",
            "Test prompt interactions using sample data.",
            "lightbulb", "Test Prompt", "#f59e0b"
        )
        self.card_test.clicked.connect(self.action_test_prompt)
        cards_layout.addWidget(self.card_test, 0, 2)
        
        # Card 4: Config
        self.card_config = HomeCard(
            "Config",
            "Adjust the application settings and preferences.",
            "tune", "Config", "#8b5cf6"
        )
        self.card_config.clicked.connect(self.action_config)
        cards_layout.addWidget(self.card_config, 0, 3)
        
        # Center the grid horizontally
        h_centered_layout = QHBoxLayout()
        h_centered_layout.addStretch()
        h_centered_layout.addLayout(cards_layout)
        h_centered_layout.addStretch()
        
        main_layout.addLayout(h_centered_layout)
        
        # Recent Files Section
        recent_box = QFrame()
        recent_box.setStyleSheet("""
            QFrame {
                background-color: palette(base);
                border-radius: 12px;
                border: 1px solid palette(mid);
            }
        """)
        recent_layout = QVBoxLayout(recent_box)
        
        recent_header_layout = QHBoxLayout()
        recent_header_layout.addWidget(QLabel("Recent Files", styleSheet="font-weight: bold; font-size: 16px;"))
        recent_header_layout.addStretch()
        clear_btn = QPushButton("Clear List")
        recent_header_layout.addWidget(clear_btn)
        recent_layout.addLayout(recent_header_layout)
        
        # Placeholder List for now
        if recent_files:
            for p in recent_files:
                row = RecentFileRow(p, "Opened recently")
                recent_layout.addWidget(row)
        else:
            empty_lbl = QLabel("No recent files")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #888888; padding: 20px;")
            recent_layout.addWidget(empty_lbl)
            
        main_layout.addWidget(recent_box)
        main_layout.addStretch()
