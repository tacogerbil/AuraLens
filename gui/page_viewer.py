"""Side-by-side page viewer: image from disk (left) + editable text (right)."""

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
)

from gui.zoomable_view import ZoomableGraphicsView


class PageViewer(QWidget):
    """Side-by-side viewer: original page image | editable extracted text."""

    re_scan_requested = Signal(int)  # page_num

    def __init__(self) -> None:
        super().__init__()
        self._image_paths: List[Path] = []
        self._page_texts: List[str] = []
        self._current_page: int = 0
        self._total_pages: int = 0

        self._setup_ui()

    # ── UI Setup ────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        """Build the splitter layout and navigation bar."""
        layout = QVBoxLayout(self)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(20)  # Wide handle for easy grabbing
        self._splitter.setChildrenCollapsible(False)  # Prevent collapsing panels
        
        # Style the splitter handle to be visible and show resize cursor
        self._splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #cccccc;
                border: 1px solid #999999;
                width: 20px;
            }
            QSplitter::handle:hover {
                background-color: #4a90e2;
            }
        """)
        
        self._setup_image_panel()
        self._setup_text_panel()
        layout.addWidget(self._splitter)

        self._setup_nav_bar(layout)
        
        # Set cursor on handle AFTER widgets are added
        if self._splitter.count() > 1:
            self._splitter.handle(1).setCursor(Qt.CursorShape.SplitHCursor)

    def _setup_image_panel(self) -> None:
        """Left panel: zoomable graphics view for page image."""
        self._scene = QGraphicsScene()
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._image_view = ZoomableGraphicsView()
        self._image_view.setScene(self._scene)
        self._splitter.addWidget(self._image_view)

    def _setup_text_panel(self) -> None:
        """Right panel: editable plain text editor."""
        self._text_edit = QPlainTextEdit()
        self._text_edit.setFont(QFont("monospace", 12))
        self._text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._splitter.addWidget(self._text_edit)
        
        # Set initial 50/50 split (resizable by user)
        self._splitter.setSizes([500, 500])

    def _setup_nav_bar(self, parent_layout: QVBoxLayout) -> None:
        """Bottom navigation: prev, page spinbox, total label, next."""
        nav = QHBoxLayout()

        self._prev_btn = QPushButton("Prev")
        self._prev_btn.clicked.connect(self._on_prev)
        nav.addWidget(self._prev_btn)

        nav.addStretch()

        nav.addWidget(QLabel("Page"))
        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(1)
        self._page_spin.setMaximum(1)
        self._page_spin.valueChanged.connect(self._on_spinbox_changed)
        nav.addWidget(self._page_spin)

        self._total_label = QLabel("of 0")
        nav.addWidget(self._total_label)

        self._re_scan_btn = QPushButton("Re-Scan Page")
        self._re_scan_btn.setToolTip("Re-process this page with the VLM")
        self._re_scan_btn.clicked.connect(self._on_re_scan)
        nav.addWidget(self._re_scan_btn)

        nav.addStretch()

        self._next_btn = QPushButton("Next")
        self._next_btn.clicked.connect(self._on_next)
        nav.addWidget(self._next_btn)

        parent_layout.addLayout(nav)

    # ── Public API ──────────────────────────────────────────────────

    def load_pages(
        self, image_paths: List[Path], page_texts: List[str]
    ) -> None:
        """Initialize viewer with image file paths and extracted texts."""
        self._image_paths = image_paths
        self._page_texts = page_texts
        self._total_pages = len(image_paths)
        self._current_page = 0

        self._page_spin.setMaximum(max(1, self._total_pages))
        self._total_label.setText(f"of {self._total_pages}")

        if self._total_pages > 0:
            self._navigate_to(1)

    def get_all_texts(self) -> List[str]:
        """Return all page texts with current edits applied."""
        self._save_current_edits()
        return list(self._page_texts)

    def current_page(self) -> int:
        """Return 1-indexed current page number."""
        return self._current_page

    # ── Navigation ──────────────────────────────────────────────────

    def _navigate_to(self, page_num: int) -> None:
        """Save current edits, load new page image and text."""
        self._save_current_edits()

        self._current_page = page_num
        self._load_page_image(page_num)
        self._load_page_text(page_num)
        self._update_nav_controls()

    def _save_current_edits(self) -> None:
        """Save text editor content back to the page_texts list."""
        if self._current_page <= 0 or self._current_page > self._total_pages:
            return
        idx = self._current_page - 1
        if idx < len(self._page_texts):
            self._page_texts[idx] = self._text_edit.toPlainText()

    def _load_page_image(self, page_num: int) -> None:
        """Load JPEG from disk and display in the graphics view."""
        idx = page_num - 1
        if idx < 0 or idx >= len(self._image_paths):
            return

        pixmap = QPixmap(str(self._image_paths[idx]))
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._image_view.fit_to_width()

    def _load_page_text(self, page_num: int) -> None:
        """Set the text editor content for the given page."""
        idx = page_num - 1
        text = self._page_texts[idx] if idx < len(self._page_texts) else ""
        self._text_edit.setPlainText(text)

    def _update_nav_controls(self) -> None:
        """Update spinbox, buttons, and label for current page."""
        self._page_spin.blockSignals(True)
        self._page_spin.setValue(self._current_page)
        self._page_spin.blockSignals(False)

        self._prev_btn.setEnabled(self._current_page > 1)
        self._next_btn.setEnabled(self._current_page < self._total_pages)

    # ── Slots ───────────────────────────────────────────────────────

    def _on_prev(self) -> None:
        """Navigate to previous page."""
        if self._current_page > 1:
            self._navigate_to(self._current_page - 1)

    def _on_next(self) -> None:
        """Navigate to next page."""
        if self._current_page < self._total_pages:
            self._navigate_to(self._current_page + 1)

    def _on_spinbox_changed(self, value: int) -> None:
        """Navigate to the page selected in the spinbox."""
        if 1 <= value <= self._total_pages and value != self._current_page:
            self._navigate_to(value)

    def _on_re_scan(self) -> None:
        """Request a re-scan of the current page."""
        if self._current_page > 0:
            self.re_scan_requested.emit(self._current_page)
