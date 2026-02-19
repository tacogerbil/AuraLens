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
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QFrame
)



# from gui.components.card import Card # Removed legacy card import
from gui.markdown_highlighter import MarkdownHighlighter
from gui.zoomable_view import ZoomableGraphicsView
from gui.components.gradient_progress_bar import GradientProgressBar
from gui.scanning_overlay import ScanningOverlay

class SplitProcessingView(QWidget):
    """
    Split view for PDF Page Preview (Left) and OCR Text Result (Right).
    """

    re_scan_requested = Signal(int)   # page_num

    run_ocr_requested = Signal()
    accept_book_requested = Signal()
    save_page_requested = Signal(int, str) # page_num, text
    config_requested = Signal()
    navigation_changed = Signal(int)  # page_num
    home_requested = Signal()

    def __init__(self, config=None) -> None:
        super().__init__()
        # If config not passed (legacy init in MainWindow might need update), load default or require it. 
        # MainWindow passes nothing currently. We need config.
        # Let's import default if None, or update MainWindow to pass it. 
        # Better to update MainWindow to pass config.
        if config is None:
             from core.config import load_config
             self._config = load_config()
        else:
             self._config = config
             
        self._image_paths: List[Path] = []
        self._page_texts: List[str] = []
        self._current_page: int = 0
        self._total_pages: int = 0
        self._is_complete: bool = False

        self._setup_ui()

    def set_ocr_completed(self, completed: bool) -> None:
        """Update UI state based on whether OCR is complete for all pages."""
        self._is_complete = completed
        self._run_ocr_btn.setVisible(not completed)
        self._accept_btn.setVisible(completed)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 12)
        layout.setSpacing(4)

        # Header: tool name left, back button right
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        title = QLabel("PDF Processor")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #334155;")
        header.addWidget(title)
        header.addStretch()

        # Action Buttons
        self._run_ocr_btn = QPushButton("Run OCR")
        self._run_ocr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_ocr_btn.clicked.connect(self.run_ocr_requested.emit)
        self._run_ocr_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        header.addWidget(self._run_ocr_btn)

        self._accept_btn = QPushButton("Accept Book")
        self._accept_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._accept_btn.clicked.connect(self.accept_book_requested.emit)
        self._accept_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #16a34a; }
        """)
        self._accept_btn.hide()
        header.addWidget(self._accept_btn)

        self._accept_btn.hide()
        header.addWidget(self._accept_btn)

        header.addSpacing(12)

        # Config Button
        config_btn = QPushButton("⚙ Config")
        config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        config_btn.clicked.connect(self.config_requested.emit)
        config_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748b;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #f1f5f9; color: #334155; }
        """)
        header.addWidget(config_btn)
        
        header.addSpacing(4)

        back_btn = QPushButton("← Dashboard")
        back_btn.setObjectName("navLink")
        back_btn.clicked.connect(self.home_requested.emit)
        header.addWidget(back_btn)
        layout.addLayout(header)

        # Splitter: PDF image (left) | OCR text (right)
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(8)
        self._splitter.setChildrenCollapsible(False)

        # Left panel
        self._preview_card, preview_content_layout = self._create_card("PDF Page Preview")
        self._scene = QGraphicsScene()
        self._image_view = ZoomableGraphicsView()
        self._image_view.setScene(self._scene)
        self._image_view.setStyleSheet("border: none; background: transparent;")
        preview_content_layout.addWidget(self._image_view)
        self._splitter.addWidget(self._preview_card)

        # Right panel
        self._text_card, text_content_layout = self._create_card("OCR Text Result")
        
        self._text_edit = QPlainTextEdit()
        self._text_edit.setFont(QFont("monospace", 11))
        self._text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._text_edit.setStyleSheet("border: none; background: transparent;")
        self._highlighter = MarkdownHighlighter(self._text_edit.document())
        text_content_layout.addWidget(self._text_edit)
        
        # Save Button Container
        save_container = QHBoxLayout()
        save_container.addStretch()
        self._save_page_btn = QPushButton("Save Page")
        self._save_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_page_btn.clicked.connect(self._on_save_page_clicked)
        self._save_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #fee2e2;
                color: #ef4444;
                border: 1px solid #fecaca;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #fecaca; }
        """)
        save_container.addWidget(self._save_page_btn)
        save_container.setContentsMargins(0, 4, 12, 4) # Padding
        
        # create_card returns content layout. We need to add this button BELOW the text edit but inside the card?
        # Text edit is in text_content_layout.
        text_content_layout.addLayout(save_container)

        self._splitter.addWidget(self._text_card)
        self._splitter.setSizes([500, 700])
        
        # Right panel content layout complete.

        # ── Navigation Bar (Center) ─────────────────
        nav = QHBoxLayout()
        nav.setSpacing(8)
        nav.addStretch()

        self._prev_btn = QPushButton("←")
        self._prev_btn.setFixedWidth(40)
        self._prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._prev_btn.clicked.connect(self._on_prev)
        nav.addWidget(self._prev_btn)

        self._page_spin = QSpinBox()
        self._page_spin.setFixedWidth(70)
        self._page_spin.setMinimum(1)
        self._page_spin.valueChanged.connect(self._on_spinbox_changed)
        nav.addWidget(self._page_spin)

        self._rescan_btn = QPushButton("↺ Rescan")
        self._rescan_btn.setToolTip("Re-run OCR on current page")
        self._rescan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rescan_btn.clicked.connect(lambda: self.re_scan_requested.emit(self._current_page))
        self._rescan_btn.setStyleSheet("""
            QPushButton {
                color: #64748b;
                background: transparent;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                color: #334155;
            }
        """)
        nav.addWidget(self._rescan_btn)

        self._nav_label_total = QLabel("/ 0")
        self._nav_label_total.setStyleSheet("color: #64748b; font-weight: 600;")
        nav.addWidget(self._nav_label_total)

        self._next_btn = QPushButton("→")
        self._next_btn.setFixedWidth(40)
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.clicked.connect(self._on_next)
        nav.addWidget(self._next_btn)
        nav.addStretch()

        # Rescan gradient progress bar
        self._rescan_bar = GradientProgressBar()
        self._rescan_bar.setRange(0, 0)
        self._rescan_bar.setFixedHeight(8)
        self._rescan_bar.setTextVisible(False)
        self._rescan_bar.setStyleSheet("QProgressBar { height: 8px; border: none; background: #f1f5f9; border-radius: 4px; }")
        self._rescan_bar.hide()
        
        # Container for Top Section (Splitter + Nav + Bar)
        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)
        top_layout.addWidget(self._splitter) # The horizontal image/text splitter
        top_layout.addLayout(nav)
        top_layout.addWidget(self._rescan_bar)
        
        # ── Main Vertical Splitter ─────────────────
        # Top: Image/Text + Nav
        # Bottom: PromptEditor
        
        from gui.components.prompt_editor_widget import PromptEditorWidget
        self._prompt_editor = PromptEditorWidget(self._config)
        
        self._main_vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self._main_vertical_splitter.setHandleWidth(8)
        self._main_vertical_splitter.setChildrenCollapsible(False)
        
        self._main_vertical_splitter.addWidget(top_container)
        self._main_vertical_splitter.addWidget(self._prompt_editor)
        
        # Default ratio: 70% content, 30% prompts (approx)
        self._main_vertical_splitter.setStretchFactor(0, 3)
        self._main_vertical_splitter.setStretchFactor(1, 1)

        layout.addWidget(self._main_vertical_splitter)

        # Scanning overlay (parented to image view)
        self._scanning_overlay = ScanningOverlay(self._image_view)
        self._scanning_overlay.hide()

    def _create_card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        """Create a styled card with a title header."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        
        # Title Header
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("""
            font-weight: bold;
            font-size: 12px;
            padding: 5px 12px;
            color: #334155;
            border-bottom: 1px solid #f1f5f9;
            background-color: transparent;
        """)
        title_lbl.setFixedHeight(26)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        card_layout.addWidget(title_lbl)
        
        # Content Area
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent; border: none;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addWidget(content_widget)
        
        return card, content_layout
        
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

    def update_page_text(self, page_num: int, text: str) -> None:
        """Update stored text for a page and refresh display if it is current."""
        idx = page_num - 1
        if 0 <= idx < len(self._page_texts):
            self._page_texts[idx] = text
        if self._current_page == page_num:
            self._text_edit.setPlainText(text)
        
    def show_scanning(self) -> None:
        self._scanning_overlay.resize(self._image_view.size())
        self._scanning_overlay.show()
        self._scanning_overlay.start()
        self._rescan_bar.setRange(0, 100)
        self._rescan_bar.setValue(0)
        self._rescan_bar.show()

    def set_rescan_progress(self, value: int) -> None:
        """Update the rescan progress bar (0-100)."""
        self._rescan_bar.setValue(value)

    def hide_scanning(self) -> None:
        self._scanning_overlay.stop()
        self._rescan_bar.setValue(100)
        self._rescan_bar.hide()
        
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

    def _on_save_page_clicked(self):
        """Emit save request with current text."""
        text = self._text_edit.toPlainText()
        # Update internal state first
        if 1 <= self._current_page <= len(self._page_texts):
             self._page_texts[self._current_page - 1] = text
        self.save_page_requested.emit(self._current_page, text)

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

    def get_system_prompt(self) -> str:
        return self._prompt_editor.get_system_prompt()

    def get_user_prompt(self) -> str:
        return self._prompt_editor.get_user_prompt()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_scanning_overlay') and self._scanning_overlay.isVisible():
             self._scanning_overlay.resize(self._image_view.size())
