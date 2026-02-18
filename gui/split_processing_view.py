"""Side-by-side processing view with headers and navigation."""

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QFrame
)

from gui.markdown_highlighter import MarkdownHighlighter
from gui.zoomable_view import ZoomableGraphicsView

class SplitProcessingView(QWidget):
    """
    Split view for PDF Page Preview (Left) and OCR Text Result (Right).
    Matches the 'Process PDF' mockup.
    """

    re_scan_requested = Signal(int)  # page_num
    navigation_changed = Signal(int) # page_num
    
    def __init__(self) -> None:
        super().__init__()
        self._image_paths: List[Path] = []
        self._page_texts: List[str] = []
        self._current_page: int = 0
        self._total_pages: int = 0

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Splitter Area
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(4) # Thinner, modern handle
        self._splitter.setChildrenCollapsible(False)
        
        # Left Panel (Image)
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_panel.setStyleSheet("background-color: palette(base); border: 1px solid palette(mid); border-radius: 8px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        left_header = QLabel("PDF Page Preview")
        left_header.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")
        left_layout.addWidget(left_header)
        
        # Separator
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)
        line1.setStyleSheet("border: none; background-color: palette(mid); height: 1px;")
        left_layout.addWidget(line1)

        # Graphics View
        self._scene = QGraphicsScene()
        self._image_view = ZoomableGraphicsView()
        self._image_view.setScene(self._scene)
        self._image_view.setStyleSheet("border: none;") 
        left_layout.addWidget(self._image_view)
        
        # Navigation Bar (Inside Left Panel per mockup? Or Bottom? Mockup shows bottom spanning both)
        # Mockup shows specific Nav bar at bottom of Left Panel? 
        # Actually mockup shows Nav bar at bottom of LEFT panel.
        
        self._nav_layout = QHBoxLayout()
        self._prev_btn = QPushButton("Back") # "Back" in mockup
        self._prev_btn.setIcon(QPixmap()) # Add icon later if needed
        self._prev_btn.clicked.connect(self._on_prev)
        
        self._next_btn = QPushButton("Next")
        self._next_btn.clicked.connect(self._on_next)
        
        self._page_label = QLabel("Page: 0 / 0") # Mockup style combo? Using Label/Spin for functionality
        self._page_spin = QSpinBox() # Keep spinbox for utility
        self._page_spin.setMinimum(1)
        self._page_spin.valueChanged.connect(self._on_spinbox_changed)
        
        self._nav_layout.addWidget(self._prev_btn)
        self._nav_layout.addStretch()
        self._nav_layout.addWidget(QLabel("Page: "))
        self._nav_layout.addWidget(self._page_spin)
        self._nav_label_total = QLabel("/ 0")
        self._nav_layout.addWidget(self._nav_label_total)
        self._nav_layout.addStretch()
        self._nav_layout.addWidget(self._next_btn)
        
        left_layout.addLayout(self._nav_layout)
        
        self._splitter.addWidget(left_panel)

        # Right Panel (Text)
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        right_panel.setStyleSheet("background-color: palette(base); border: 1px solid palette(mid); border-radius: 8px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        right_header = QLabel("OCR Text Result")
        right_header.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")
        right_layout.addWidget(right_header)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        line2.setStyleSheet("border: none; background-color: palette(mid); height: 1px;")
        right_layout.addWidget(line2)

        self._text_edit = QPlainTextEdit()
        self._text_edit.setFont(QFont("monospace", 11))
        self._text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._text_edit.setStyleSheet("border: none;") 
        self._highlighter = MarkdownHighlighter(self._text_edit.document())
        right_layout.addWidget(self._text_edit)
        
        self._splitter.addWidget(right_panel)
        self._splitter.setSizes([400, 600]) # Initial split

        layout.addWidget(self._splitter)
        
        # Add Scanning Overlay
        from gui.scanning_overlay import ScanningOverlay
        self._scanning_overlay = ScanningOverlay(left_panel) # Overlay on LEFT panel or whole?
        # Mockup implies left panel preview changes?
        # Let's verify existing behavior. PageViewer overlays the whole widget.
        # I'll overlay the left panel (image) primarily.
        self._scanning_overlay = ScanningOverlay(self._image_view)
        self._scanning_overlay.hide()
        
    # ── Public API (Same as PageViewer for compatibility) ──────────────────

    def load_pages(self, image_paths: List[Path], page_texts: List[str]) -> None:
        self._image_paths = image_paths
        self._page_texts = page_texts
        self._total_pages = len(image_paths)
        self._current_page = 0
        
        self._page_spin.setMaximum(max(1, self._total_pages))
        self._nav_label_total.setText(f"/ {self._total_pages}")
        
        if self._total_pages > 0:
            self._navigate_to(1)
            
    def navigate_to(self, page_num: int) -> None:
        """Jump to specific page number (1-indexed)."""
        if 1 <= page_num <= self._total_pages:
            self._navigate_to(page_num)

    def get_all_texts(self) -> List[str]:
        self._save_current_edits()
        return list(self._page_texts)
        
    def current_page(self) -> int:
        return self._current_page
        
    def show_scanning(self) -> None:
        self._scanning_overlay.resize(self._image_view.size())
        self._scanning_overlay.show()
        self._scanning_overlay.start()
        
    def hide_scanning(self) -> None:
        self._scanning_overlay.stop()
        
    # ── Internal Logic ──────────────────────────────────────────────

    def _navigate_to(self, page_num: int) -> None:
        self._save_current_edits()
        
        self._current_page = page_num
        self._load_page_image(page_num)
        self._load_page_text(page_num)
        
        self._page_spin.blockSignals(True)
        self._page_spin.setValue(page_num)
        self._page_spin.blockSignals(False)
        
        self._prev_btn.setEnabled(page_num > 1)
        self._next_btn.setEnabled(page_num < self._total_pages)
        
        self.navigation_changed.emit(page_num)

    def _save_current_edits(self) -> None:
        if 1 <= self._current_page <= len(self._page_texts):
             self._page_texts[self._current_page - 1] = self._text_edit.toPlainText()

    def _load_page_image(self, page_num: int) -> None:
        idx = page_num - 1
        if 0 <= idx < len(self._image_paths):
            pixmap = QPixmap(str(self._image_paths[idx]))
            self._scene.clear()
            self._scene.addPixmap(pixmap)
            self._image_view.fit_to_width()

    def _load_page_text(self, page_num: int) -> None:
        idx = page_num - 1
        text = self._page_texts[idx] if 0 <= idx < len(self._page_texts) else ""
        self._text_edit.setPlainText(text)

    def _on_prev(self):
        if self._current_page > 1:
            self._navigate_to(self._current_page - 1)
            
    def _on_next(self):
        if self._current_page < self._total_pages:
            self._navigate_to(self._current_page + 1)
            
    def _on_spinbox_changed(self, val):
        if 1 <= val <= self._total_pages:
            self._navigate_to(val)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_scanning_overlay') and self._scanning_overlay.isVisible():
             self._scanning_overlay.resize(self._image_view.size())
