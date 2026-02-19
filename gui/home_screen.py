"""Home Screen Dashboard (Reference Implementation Compliance)."""

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame
)

from gui.components.dashboard_card import DashboardCard

class HomeScreen(QWidget):
    """
    Main Dashboard Page based on 'Modern PDF OCR App' reference.
    """

    action_open_pdf = Signal()
    action_process_pdf = Signal()
    action_test_prompt = Signal()
    action_config = Signal()
    
    def __init__(self, recent_files: List[Path] = None):
        super().__init__()
        
        layout = QVBoxLayout(self)
        layout.setSpacing(30)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Header (Reference Style: #mainTitle)
        header = QLabel("PDF Processor")
        header.setObjectName("mainTitle")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Style is applied globally via ThemeManager now
        layout.addWidget(header)
        
        # Grid of Cards
        grid = QGridLayout()
        grid.setSpacing(30)
        
        cards_data = [
            ("Open PDF", "Select a PDF file to begin processing.", "#ffffff", self.action_open_pdf),
            ("Process PDF", "Run OCR and verify extracted text.", "#ffffff", self.action_process_pdf),
            ("Test Prompt", "Test your OCR prompt formatting.", "#ffffff", self.action_test_prompt),
            ("Config", "Adjust application settings.", "#ffffff", self.action_config)
        ]
        
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        
        for (title, desc, color, signal), pos in zip(cards_data, positions):
            card = DashboardCard(title, desc, color)
            # Connect the card click to the signal
            card.clicked.connect(signal.emit)
            grid.addWidget(card, *pos)
            
        layout.addLayout(grid)

        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #64748b; font-size: 13px; padding: 4px;")
        layout.addWidget(self._status_label)

        layout.addStretch()

    def set_current_file(self, path: Path, status: str) -> None:
        """Show the loaded file name and its cache status on the dashboard."""
        if path:
            self._status_label.setText(f"{path.name}  [{status}]")
        else:
            self._status_label.setText("")

