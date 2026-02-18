"""Home Screen Dashboard with Navigation Cards and Recent Files."""

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSpacerItem,
    QSizePolicy
)

from gui.components.card import Card
from gui.theme_manager import ThemeManager

class ActionCard(Card):
    """
    Interactive Card for Home Screen Actions.
    Inherits from the shared Card component for styling.
    """
    
    clicked = Signal()

    def __init__(self, title: str, description: str, icon_char: str, action_text: str, color_accent: str):
        super().__init__(accent_color=color_accent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(240, 280) # Slightly larger for better spacing

        # Layout provided by Card's internal structure
        # We add widgets to it using add_widget / add_layout or accessing layout directly
        
        # 1. Icon Area
        self._icon_label = QLabel(icon_char)
        self._icon_label.setFixedSize(64, 64)
        self._icon_label.setStyleSheet(f"""
            background-color: {color_accent};
            border-radius: 32px;
            color: white;
            font-size: 24px;
            font-weight: bold;
        """)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_container = QHBoxLayout()
        icon_container.addStretch()
        icon_container.addWidget(self._icon_label)
        icon_container.addStretch()
        self.add_layout(icon_container)
        
        # 2. Title
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.add_widget(title_lbl)
        
        # 3. Description
        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setStyleSheet("color: palette(text); opacity: 0.8; font-size: 13px; border: none;")
        self.add_widget(desc_lbl)
        
        self.add_stretch()
        
        # 4. Action Button
        action_btn = QPushButton(action_text)
        action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
                background-color: {color_accent}; /* Let opacity handle hover if needed or brightness */
                border: 2px solid rgba(255,255,255,0.2);
            }}
        """)
        action_btn.clicked.connect(self.clicked)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(action_btn)
        self.add_layout(btn_layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

class RecentFileRow(QFrame):
    """Row item for Recent Files list."""
    
    open_requested = Signal(Path)

    def __init__(self, path: Path, date_str: str):
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # Icon
        icon_lbl = QLabel("PDF")
        icon_lbl.setFixedSize(32, 32)
        icon_lbl.setStyleSheet("background-color: #e81123; color: white; border-radius: 4px; padding: 4px;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)
        
        # Details
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        name_lbl = QLabel(path.name)
        name_lbl.setStyleSheet("font-weight: bold; font-size: 14px; border: none; background: transparent;")
        path_lbl = QLabel(str(path.parent))
        path_lbl.setStyleSheet("color: palette(text); opacity: 0.7; font-size: 12px; border: none; background: transparent;")
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(path_lbl)
        layout.addLayout(info_layout)
        
        layout.addStretch()
        
        # Date
        date_lbl = QLabel(date_str)
        date_lbl.setStyleSheet("color: palette(text); opacity: 0.5; border: none; background: transparent;")
        layout.addWidget(date_lbl)
        
        # Styling for hover effect
        self.setStyleSheet("""
            RecentFileRow {
                background-color: transparent;
                border-radius: 6px;
            }
            RecentFileRow:hover {
                background-color: palette(alternate-base);
            }
        """)

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
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: palette(text); margin-bottom: 10px;")
        main_layout.addWidget(header)
        
        # Current File Indicator
        self._current_file_label = QLabel("No file loaded")
        self._current_file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._current_file_label.setStyleSheet("color: palette(midlight); font-size: 14px;")
        main_layout.addWidget(self._current_file_label)
        
        # Cards Grid
        cards_layout = QHBoxLayout() # Changed to HBox for centering flow
        cards_layout.setSpacing(20)
        cards_layout.addStretch()
        
        # Card 1: Open PDF
        self.card_open = ActionCard(
            "Open PDF", 
            "Select a PDF file to open and begin processing.",
            "📂", "Open PDF", "#3b82f6"
        )
        self.card_open.clicked.connect(self.action_open_pdf)
        cards_layout.addWidget(self.card_open)
        
        # Card 2: Process PDF
        self.card_process = ActionCard(
            "Process PDF",
            "Run OCR on the PDF to extract and verify text.",
            "⚙️", "Process PDF", "#10b981"
        )
        self.card_process.clicked.connect(self.action_process_pdf)
        cards_layout.addWidget(self.card_process)

        # Card 3: Test Prompt
        self.card_test = ActionCard(
            "Test Prompt",
            "Test prompt interactions using sample data.",
            "💡", "Test Prompt", "#f59e0b"
        )
        self.card_test.clicked.connect(self.action_test_prompt)
        cards_layout.addWidget(self.card_test)
        
        # Card 4: Config
        self.card_config = ActionCard(
            "Config",
            "Adjust the application settings and preferences.",
            "🔧", "Config", "#8b5cf6"
        )
        self.card_config.clicked.connect(self.action_config)
        cards_layout.addWidget(self.card_config)
        
        cards_layout.addStretch()
        main_layout.addLayout(cards_layout)
        
        # Recent Files Section - Wrapped in Card
        recent_card = Card(title="Recent Files")
        recent_layout = QVBoxLayout() # Inner layout for content
        
        # Header inside card (Title is handled by Card, but we might want button)
        # Card title wraps nicely. Let's add the Clear button to the header area? 
        # The Card component puts title in a VBox. 
        # Let's just put the list in the card for now.
        
        if recent_files:
            for p in recent_files:
                row = RecentFileRow(p, "Opened recently")
                recent_layout.addWidget(row)
        else:
            empty_lbl = QLabel("No recent files")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: palette(text); opacity: 0.6; padding: 20px; border: none;")
            recent_layout.addWidget(empty_lbl)
            
        recent_card.add_layout(recent_layout)
        
        # Add "Clear List" button at bottom of recent card?
        # Or maybe we want a custom header for Recent Files Card to include the button.
        # For MCCC simplicity, let's append the button at the bottom for now.
        if recent_files:
            clear_btn = QPushButton("Clear List")
            clear_btn.setFlat(True)
            clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            clear_btn.setStyleSheet("text-align: right; color: palette(text); opacity: 0.7;")
            # clear_btn.clicked.connect(...) 
            recent_card.add_widget(clear_btn)

        main_layout.addWidget(recent_card)
        main_layout.addStretch()

    def set_current_file(self, path: Path, status: str) -> None:
        """Update the file status label."""
        self._current_file_label.setText(f"{path.name} — {status}")

